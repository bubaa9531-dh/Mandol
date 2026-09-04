"""Service-logic tests for the AML adapter using a lightweight Mandol stub.

These tests exercise the full Add -> Search -> retention chain of
``mandol_aml.memory.MemoryService`` without requiring PyTorch / an embedding
model / network. A minimal stub mimics the Mandol API surface the adapter uses
(SemanticMap/SemanticGraph/MemoryUnit), so the tests verify the *adapter* logic:
synchronous storage, per-user_id isolation, relevance ordering, top_k bounds,
idempotent re-Add and purge/retention.

Run with:  pytest tests/test_service_logic.py -v
"""

from __future__ import annotations

import sys
import types
import uuid
from typing import Any, Dict, List, Optional, Set

import pytest

from mandol_aml.config import Settings
from mandol_aml.memory import MemoryService


# --------------------------------------------------------------------------- #
# Minimal Mandol stub (module-level, installed into sys.modules)              #
# --------------------------------------------------------------------------- #
class StubMemoryUnit:
    def __init__(self, uid, raw_data, metadata=None, embedding=None, sparse_embedding=None):
        self.uid = uid
        self.raw_data = raw_data
        self.metadata = metadata or {}
        self.embedding = embedding
        self.sparse_embedding = sparse_embedding
        self.text_cached = str(raw_data.get("text_content") or "") or uid


class StubSemanticMap:
    def __init__(self, *args, **kwargs):
        self.memory_units: Dict[str, StubMemoryUnit] = {}
        self.memory_spaces: Dict[str, dict] = {}
        self._space_members: Dict[str, Set[str]] = {}

    def create_memory_space(self, name):
        return self.memory_spaces.setdefault(name, {})

    def _unit_space_uids(self, names: List[str]) -> Set[str]:
        uids: Set[str] = set()
        for n in names:
            uids |= self._space_members.get(n, set())
        return uids


class StubSemanticGraph:
    def __init__(self, semantic_map_instance=None):
        self.semantic_map = semantic_map_instance or StubSemanticMap()
        self._closed = False

    def connect_to_l2(self, *args, **kwargs):
        return True

    def close(self):
        self._closed = True

    def create_memory_space_in_map(self, name):
        self.semantic_map.memory_spaces.setdefault(name, {})
        self.semantic_map._space_members.setdefault(name, set())

    def batch_add_units(self, units, space_names=None, generate_sparse_embedding=True, show_progress=True):
        added = 0
        for unit in units:
            existing = self.semantic_map.memory_units.get(unit.uid)
            if existing is not None and existing.raw_data == unit.raw_data:
                continue  # idempotent skip, like Mandol
            self.semantic_map.memory_units[unit.uid] = unit
            added += 1
            for space in space_names or []:
                self.semantic_map._space_members.setdefault(space, set()).add(unit.uid)
        return {"added": added}

    def get_units_in_memory_space(self, ms_names, recursive=True):
        if isinstance(ms_names, str):
            ms_names = [ms_names]
        uids = self.semantic_map._unit_space_uids(list(ms_names or []))
        return [self.semantic_map.memory_units[u] for u in uids if u in self.semantic_map.memory_units]

    def get_all_units(self):
        return list(self.semantic_map.memory_units.values())

    def delete_unit(self, uid, rebuild_semantic_map_index_immediately=False):
        self.semantic_map.memory_units.pop(uid, None)
        for members in self.semantic_map._space_members.values():
            members.discard(uid)

    def search_similarity_in_graph(self, query_text=None, top_k=5, ms_names=None, return_score=False, **kwargs):
        if ms_names:
            units = self.get_units_in_memory_space(ms_names)
        else:
            units = self.get_all_units()
        query_tokens = [t.lower() for t in (query_text or "").split() if t]
        scored = []
        for unit in units:
            text = (unit.text_cached or "").lower()
            score = sum(1 for t in query_tokens if t in text)
            if score > 0:
                scored.append((unit, float(score)))
        scored.sort(key=lambda x: (-x[1], x[0].uid))
        scored = scored[:top_k]
        if return_score:
            return scored
        return [u for u, _ in scored]


def _install_mandol_stub() -> None:
    mod = types.ModuleType("mandol")
    mod.MemoryUnit = StubMemoryUnit
    mod.SemanticMap = StubSemanticMap
    mod.SemanticGraph = StubSemanticGraph
    sys.modules["mandol"] = mod


@pytest.fixture(autouse=True)
def _stub_mandol():
    previous = sys.modules.get("mandol")
    _install_mandol_stub()
    try:
        yield
    finally:
        # Restore any pre-existing module so we never leak the stub into a
        # session where the real mandol package is installed.
        if previous is None:
            sys.modules.pop("mandol", None)
        else:
            sys.modules["mandol"] = previous


def _make_service(backend: str = "shared") -> MemoryService:
    settings = Settings(
        host="127.0.0.1",
        port=8000,
        backend=backend,
        retrieval_mode="graph",
        warmup_on_start=False,
        high_level_memory=False,
        generate_sparse_embedding=False,
    )
    service = MemoryService(settings)
    service.start()
    assert service.ready
    return service


def _chunk(user_id: str, session_id: str, messages) -> dict:
    return {
        "request_id": f"eval:run:{user_id}:{uuid.uuid4().hex[:6]}",
        "messages": messages,
        "user_id": user_id,
        "session_id": session_id,
    }


def test_add_then_search_shared_backend_isolation_and_order() -> None:
    service = _make_service("shared")
    user_a = "user_A"
    user_b = "user_B"

    service.add_messages(
        user_a, "sess-a",
        "req-a-1",
        [
            {"role": "user", "content": "Zhang San travelled to Beijing in June."},
            {"role": "user", "content": "Li Si prefers quiet hotels in Shanghai."},
        ],
    )
    service.add_messages(
        user_b, "sess-b", "req-b-1",
        [{"role": "user", "content": "Wang Wu is allergic to peanuts."}],
    )

    hits_a = service.search(user_a, "Where did Zhang San travel?", top_k=10)
    # user A only, never B's memory
    assert all("Wang Wu" not in h["content"] for h in hits_a)
    assert all("Zhang San" in h["content"] for h in hits_a)
    assert len(hits_a) <= 10

    hits_b = service.search(user_b, "What is Wang Wu allergic to?", top_k=10)
    assert hits_b and "peanuts" in hits_b[0]["content"]
    assert all("Zhang San" not in h["content"] for h in hits_b)

    # ids and content present, scores descending
    scores = [h["score"] for h in hits_a if h["score"] is not None]
    assert scores == sorted(scores, reverse=True)
    for h in hits_a:
        assert h["id"] and h["content"]
    service.shutdown()


def test_top_k_and_empty_search() -> None:
    service = _make_service("shared")
    service.add_messages("u1", "s1", "r1", [{"role": "user", "content": f"unique token alpha {i}"} for i in range(5)])
    hits = service.search("u1", "alpha", top_k=2)
    assert len(hits) <= 2
    assert service.search("u_no_memory", "anything", top_k=5) == []
    service.shutdown()


def test_readd_is_idempotent() -> None:
    service = _make_service("shared")
    chunk = _chunk("u1", "s1", [{"role": "user", "content": "A stable fact to remember."}])
    first = service.add_messages(chunk["user_id"], chunk["session_id"], chunk["request_id"], chunk["messages"])
    second = service.add_messages(chunk["user_id"], chunk["session_id"], chunk["request_id"], chunk["messages"])
    assert first == 1
    assert second == 1  # same request_id -> same uids -> deduplicated
    assert service.stats()["units"] == 1
    service.shutdown()


def test_purge_user_and_stats() -> None:
    service = _make_service("shared")
    service.add_messages("u1", "s1", "r1", [{"role": "user", "content": "fact one"}])
    service.add_messages("u2", "s2", "r2", [{"role": "user", "content": "fact two"}])
    assert service.stats()["units"] == 2
    assert service.purge_user("u1") is True
    assert service.stats()["units"] == 1
    assert service.search("u1", "fact one", top_k=5) == []
    assert service.search("u2", "fact two", top_k=5)
    service.shutdown()


def test_isolated_backend_basic() -> None:
    service = _make_service("isolated")
    service.add_messages("u1", "s1", "r1", [{"role": "user", "content": "memory for user one only"}])
    service.add_messages("u2", "s2", "r2", [{"role": "user", "content": "memory for user two only"}])
    h1 = service.search("u1", "memory for user one", top_k=5)
    assert h1 and "user one" in h1[0]["content"]
    assert all("user two" not in h["content"] for h in h1)
    service.shutdown()
