"""Per-user memory management backed by Mandol's SemanticMap / SemanticGraph.

Design
------
Mandol keeps its semantic index and graph in process memory. The AML contract
defines ``user_id`` as the *only* retrieval-isolation boundary: memory written
for one ``user_id`` must never be returned for another ``user_id``.

Two backends are provided:

* ``shared`` (default): a single SemanticMap/SemanticGraph is created for the
  process and every AML ``user_id`` is isolated by its own MemorySpace. Writes
  and dense retrieval are always scoped to that space. This is memory-light and
  works well when an evaluation run contains many users.

* ``isolated``: one SemanticMap/SemanticGraph per AML ``user_id``. Mandol's
  global model manager still shares the underlying embedding model weights, so
  the extra cost is per-user index state. This layout also allows Mandol's
  space-agnostic ``MultiRetriever`` hybrid path (cosine + BM25 + optional
  SPLADE/rerank) without any cross-user leakage, at the cost of more memory.

Mandol itself is never modified: we only call its public API.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .config import Settings

logger = logging.getLogger("mandol_aml.memory")


def _space_name_for(user_id: str) -> str:
    digest = hashlib.sha1(user_id.encode("utf-8")).hexdigest()[:16]
    return f"u_{digest}"


def _uid_for(space: str, request_id: str, index: int) -> str:
    digest = hashlib.sha1(f"{request_id}::{index}".encode("utf-8")).hexdigest()[:24]
    return f"{space[:8]}_{digest}"


def _iso_from_ms(ts_ms: Optional[int]) -> Optional[str]:
    if ts_ms is None:
        return None
    try:
        return (
            datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except Exception:
        return None


class _UserState:
    """Bookkeeping for one AML user_id."""

    __slots__ = ("user_id", "space", "graph", "last_active", "dirty_high_level")

    def __init__(self, user_id: str, space: str, graph: Any = None) -> None:
        self.user_id = user_id
        self.space = space
        self.graph = graph
        self.last_active: float = time.time()
        self.dirty_high_level: bool = False


class MemoryService:
    """Thread-safe AML memory service implemented with Mandol core objects."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.RLock()
        self._ready = False
        self._init_error: Optional[str] = None

        # shared backend state
        self._graph: Any = None
        self._shared_units_created: bool = False

        # isolated backend state
        self._users: Dict[str, _UserState] = {}

        # module-level handles (imported lazily to keep startup light)
        self._MemoryUnit: Any = None

    # ------------------------------------------------------------------ lifecycle
    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error

    def start(self) -> None:
        """Create the Mandol runtime. Health stays 503 until this succeeds."""
        with self._lock:
            if self._ready:
                return
            try:
                self._ensure_core()
                self._ensure_shared_graph_locked()
                if self.settings.l2_dir and self._graph is not None:
                    try:
                        self._graph.connect_to_l2(
                            l2_base_path=os.path.join(self.settings.l2_dir, "shared"),
                            max_capacity=1_000_000,
                            high_watermark=0.85,
                            low_watermark=0.70,
                        )
                        logger.info("RocksDB tiered paging enabled at %s", self.settings.l2_dir)
                    except Exception as exc:  # pragma: no cover - depends on Mandol runtime
                        logger.warning("connect_to_l2 failed (continuing in memory-only mode): %s", exc)
                if self.settings.warmup_on_start and self._graph is not None:
                    # Force one embedding so the model is downloaded/loaded before
                    # the platform starts calling Add/Search.
                    self._warmup_locked()
                self._ready = True
                logger.info("MemoryService ready (backend=%s, model=%s)", self.settings.backend, self.settings.embedding_model)
            except Exception as exc:  # pragma: no cover
                self._init_error = str(exc)
                logger.exception("MemoryService failed to initialize: %s", exc)
                raise

    def _ensure_core(self) -> None:
        from mandol import MemoryUnit, SemanticGraph, SemanticMap

        self._MemoryUnit = MemoryUnit
        if self.settings.backend == "isolated":
            # ensure class imported for validation
            _ = (SemanticGraph, SemanticMap)

    def _ensure_shared_graph_locked(self) -> None:
        if self.settings.backend == "shared" and self._graph is None:
            from mandol import SemanticGraph, SemanticMap

            semantic_map = SemanticMap(
                embedding_model_name=self.settings.embedding_model,
                embedding_dim=self.settings.embedding_dim,
                use_flash_attention=self.settings.use_flash_attention or None,
            )
            self._graph = SemanticGraph(semantic_map_instance=semantic_map)

    def _new_user_graph_locked(self) -> Any:
        from mandol import SemanticGraph, SemanticMap

        semantic_map = SemanticMap(
            embedding_model_name=self.settings.embedding_model,
            embedding_dim=self.settings.embedding_dim,
            use_flash_attention=self.settings.use_flash_attention or None,
        )
        return SemanticGraph(semantic_map_instance=semantic_map)

    def _warmup_locked(self) -> None:
        if self.settings.backend == "isolated":
            graph = self._new_user_graph_locked()
            # Embed a harmless probe string; the result is discarded.
            probe = self._MemoryUnit(
                uid="__aml_warmup__",
                raw_data={"text_content": "AML warm-up probe."},
                metadata={"aml": True},
            )
            graph.batch_add_units(
                [probe],
                generate_sparse_embedding=False,
                show_progress=False,
            )
            graph.delete_unit("__aml_warmup__")
        elif self._graph is not None:
            probe = self._MemoryUnit(
                uid="__aml_warmup__",
                raw_data={"text_content": "AML warm-up probe."},
                metadata={"aml": True},
            )
            self._graph.batch_add_units(
                [probe],
                space_names=["__aml_warmup__"],
                generate_sparse_embedding=False,
                show_progress=False,
            )
            self._graph.delete_unit("__aml_warmup__")
            try:
                self._graph.semantic_map.memory_spaces.pop("__aml_warmup__", None)
            except Exception:
                pass

    def _get_or_create_user_locked(self, user_id: str) -> _UserState:
        state = self._users.get(user_id)
        if state is None:
            space = _space_name_for(user_id)
            graph = None
            if self.settings.backend == "isolated":
                graph = self._new_user_graph_locked()
            state = _UserState(user_id=user_id, space=space, graph=graph)
            self._users[user_id] = state
        state.last_active = time.time()
        return state

    # --------------------------------------------------------------------- Add
    def add_messages(
        self,
        user_id: str,
        session_id: str,
        request_id: str,
        messages: List[Dict[str, Any]],
    ) -> int:
        """Store a chunk of messages synchronously and return the count stored."""
        with self._lock:
            if not self._ready:
                raise RuntimeError("memory service is not ready")
            self._ensure_shared_graph_locked()
            state = self._get_or_create_user_locked(user_id)

            units = []
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            for index, msg in enumerate(messages):
                content = str(msg.get("content") or "").strip()
                if not content:
                    continue
                role = str(msg.get("role") or "user")
                ts_ms = msg.get("timestamp")
                uid = _uid_for(state.space, request_id, index)
                metadata = {
                    "aml": True,
                    "user_id": user_id,
                    "session_id": session_id,
                    "request_id": request_id,
                    "role": role,
                    "turn_index": index,
                    "ts_ms": ts_ms,
                    "created": now_iso,
                }
                units.append(
                    self._MemoryUnit(
                        uid=uid,
                        raw_data={"text_content": content},
                        metadata=metadata,
                    )
                )

            if not units:
                return 0

            if self.settings.backend == "isolated":
                assert state.graph is not None
                state.graph.batch_add_units(
                    units,
                    generate_sparse_embedding=self.settings.generate_sparse_embedding,
                    show_progress=False,
                )
            else:
                assert self._graph is not None
                if state.space not in self._graph.semantic_map.memory_spaces:
                    self._graph.create_memory_space_in_map(state.space)
                self._graph.batch_add_units(
                    units,
                    space_names=[state.space],
                    generate_sparse_embedding=self.settings.generate_sparse_embedding,
                    show_progress=False,
                )

            state.dirty_high_level = True
            self._maybe_high_level_async(state, units)
            return len(units)

    # ------------------------------------------------------------------ Search
    def search(self, user_id: str, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Retrieve ranked memory evidence for one user_id (no cross-user leak)."""
        with self._lock:
            if not self._ready:
                raise RuntimeError("memory service is not ready")
            state = self._users.get(user_id)
            if state is None:
                return []
            state.last_active = time.time()
            self._maybe_high_level_wait(state)

            if self.settings.backend == "isolated":
                assert state.graph is not None
                if self.settings.retrieval_mode == "hybrid":
                    hits = self._search_hybrid(state.graph, query, top_k)
                else:
                    hits = self._search_dense(state.graph, query, top_k, ms_names=None)
            else:
                assert self._graph is not None
                hits = self._search_dense(self._graph, query, top_k, ms_names=[state.space])
            return hits[:top_k]

    def _search_dense(
        self,
        graph: Any,
        query: str,
        top_k: int,
        ms_names: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        try:
            results = graph.search_similarity_in_graph(
                query_text=query,
                top_k=top_k,
                ms_names=ms_names,
                return_score=True,
            )
        except Exception as exc:  # pragma: no cover - depends on Mandol runtime
            logger.warning("dense search failed for user: %s", exc)
            return []
        return [self._hit_from(unit, score) for unit, score in results]

    def _search_hybrid(self, graph: Any, query: str, top_k: int) -> List[Dict[str, Any]]:
        try:
            retriever = graph.get_multi_retriever()
            results = retriever.smart_search(
                query=query,
                methods=list(self.settings.retrieval_methods),
                top_k=top_k,
                rerank_method=self.settings.rerank_method,
                return_detailed=False,
            )
            if isinstance(results, dict):
                results = results.get("results", [])
        except Exception as exc:  # pragma: no cover - depends on Mandol runtime
            logger.warning("hybrid search failed, falling back to dense: %s", exc)
            return self._search_dense(graph, query, top_k, ms_names=None)
        return [self._hit_from(unit, score) for unit, score in results]

    @staticmethod
    def _hit_from(unit: Any, score: Any) -> Dict[str, Any]:
        content = getattr(unit, "text_cached", None) or ""
        if not content:
            raw = getattr(unit, "raw_data", {}) or {}
            content = str(raw.get("text_content") or "") or str(unit.uid)
        metadata = getattr(unit, "metadata", {}) or {}
        created_at = _iso_from_ms(metadata.get("ts_ms")) or metadata.get("created")
        try:
            score_f = float(score)
            if score_f != score_f:  # NaN guard
                score_f = None
        except Exception:
            score_f = None
        return {
            "id": unit.uid,
            "content": content,
            "score": score_f,
            "created_at": created_at,
        }

    # ------------------------------------------------------------- high-level
    def _maybe_high_level_async(self, state: _UserState, units: List[Any]) -> None:
        if not self.settings.high_level_memory:
            return
        from .high_level import schedule_high_level_build

        schedule_high_level_build(self, state, units, self.settings)

    def _maybe_high_level_wait(self, state: _UserState) -> None:
        if not self.settings.high_level_memory:
            return
        wait = self.settings.high_level_wait_on_search_seconds
        if wait <= 0:
            return
        from .high_level import wait_for_pending_build

        wait_for_pending_build(self, state, wait)

    def l0_units_for(self, state: _UserState) -> List[Any]:
        """Return the base (L0) units belonging to one user."""
        if self.settings.backend == "isolated":
            assert state.graph is not None
            return list(state.graph.get_all_units())
        assert self._graph is not None
        return self._graph.get_units_in_memory_space(state.space, recursive=True)

    # ----------------------------------------------------------------- cleanup
    def purge_user(self, user_id: str) -> bool:
        """Delete all memory of one user (compliance / retention)."""
        with self._lock:
            state = self._users.get(user_id)
            if state is None:
                return False
            try:
                if self.settings.backend == "isolated" and state.graph is not None:
                    for unit in list(state.graph.get_all_units()):
                        state.graph.delete_unit(unit.uid)
                    try:
                        state.graph.close()
                    except Exception:
                        pass
                else:
                    assert self._graph is not None
                    for unit in self._graph.get_units_in_memory_space(state.space, recursive=True):
                        self._graph.delete_unit(unit.uid)
            except Exception as exc:  # pragma: no cover
                logger.warning("purge_user(%s) partial failure: %s", user_id, exc)
            self._users.pop(user_id, None)
            logger.info("purged memory for user %s", user_id)
            return True

    def purge_idle(self, ttl_days: float) -> int:
        """Purge users idle for more than ttl_days (default 30-day retention)."""
        cutoff = time.time() - ttl_days * 86400.0
        victims = [uid for uid, st in self._users.items() if st.last_active < cutoff]
        for uid in victims:
            self.purge_user(uid)
        return len(victims)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            if self.settings.backend == "isolated":
                users = len(self._users)
                units = sum(len(st.graph.get_all_units()) for st in self._users.values() if st.graph is not None)
                spaces = 0
            else:
                users = len(self._users)
                units = len(self._graph.semantic_map.memory_units) if self._graph is not None else 0
                spaces = len(self._graph.semantic_map.memory_spaces) if self._graph is not None else 0
            return {
                "backend": self.settings.backend,
                "ready": self._ready,
                "users": users,
                "units": units,
                "spaces": spaces,
                "retrieval_mode": self.settings.retrieval_mode,
            }

    def shutdown(self) -> None:
        with self._lock:
            for uid in list(self._users.keys()):
                try:
                    self.purge_user(uid)
                except Exception:
                    pass
