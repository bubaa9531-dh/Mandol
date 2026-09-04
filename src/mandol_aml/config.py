"""Runtime configuration for the AML adapter.

All settings are read from environment variables prefixed with ``AML_`` so the
adapter can be tuned without touching Mandol code. The default path is fully
local: Mandol's dense graph retrieval works as soon as the embedding model is
available; no provider LLM key is required unless the optional high-level
memory feature is enabled.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_list(name: str, default: Optional[List[str]] = None) -> List[str]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return list(default or [])
    return [x.strip() for x in raw.split(",") if x.strip()]


@dataclass
class Settings:
    # --- HTTP server -------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000
    add_path: str = "/add"
    search_path: str = "/search"
    health_path: str = "/health"

    # --- Authentication -----------------------------------------------------
    # Memory System Key issued by the participant for the AML platform.
    # Empty => unauthenticated endpoints. AML allows "none" only for the public
    # smoke compatibility check, so set a strong key before a formal run.
    memory_system_key: str = ""

    # --- Mandol runtime -----------------------------------------------------
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_dim: Optional[int] = None
    use_flash_attention: bool = False
    # Build SPLADE sparse vectors during Add. Improves hybrid retrieval quality
    # but slows writes and requires downloading the SPLADE model.
    generate_sparse_embedding: bool = False
    # Backend layout:
    #   "shared"   -> one SemanticMap/SemanticGraph for the process, each AML
    #                 user_id isolated by its own MemorySpace (memory-light,
    #                 dense retrieval only).
    #   "isolated" -> one SemanticMap/SemanticGraph per AML user_id (model
    #                 weights are still shared through Mandol's model manager),
    #                 which also allows the space-agnostic MultiRetriever
    #                 hybrid path without cross-user leakage.
    backend: str = "shared"
    # Retrieval path used by the "isolated" backend:
    #   "graph"  -> SemanticGraph.search_similarity_in_graph (dense, robust)
    #   "hybrid" -> MultiRetriever.smart_search over cosine + bm25 (+ splade)
    retrieval_mode: str = "graph"
    retrieval_methods: List[str] = field(default_factory=lambda: ["cosine", "bm25"])
    rerank_method: Optional[str] = None
    # Pre-load the embedding model at startup so the first Add is not slowed by
    # model download / warm-up. Health returns 503 until warm-up finishes.
    warmup_on_start: bool = True

    # --- Storage / capacity -------------------------------------------------
    l2_dir: Optional[str] = None  # optional RocksDB tiered paging directory
    max_units_per_user: Optional[int] = None

    # --- Retention (AML requires deleting evaluation data within 30 days) ----
    data_ttl_days: int = 30
    retention_interval_seconds: int = 3600

    # --- Rate limiting / capacity -------------------------------------------
    rate_limit_rpm: int = 0  # 0 = unlimited
    max_request_bytes: int = 10 * 1024 * 1024
    add_timeout_seconds: float = 60.0
    search_timeout_seconds: float = 30.0

    # --- Optional high-level memory (experimental, default off) --------------
    high_level_memory: bool = False
    high_level_debounce_seconds: float = 5.0
    high_level_wait_on_search_seconds: float = 0.0

    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        embedding_dim = _get_int("AML_EMBEDDING_DIM", 0)
        s = cls(
            host=os.getenv("AML_HOST", "0.0.0.0"),
            port=_get_int("AML_PORT", 8000),
            add_path=os.getenv("AML_ADD_PATH", "/add") or "/add",
            search_path=os.getenv("AML_SEARCH_PATH", "/search") or "/search",
            health_path=os.getenv("AML_HEALTH_PATH", "/health") or "/health",
            memory_system_key=os.getenv("AML_MEMORY_SYSTEM_KEY", "") or "",
            embedding_model=os.getenv("AML_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B") or "Qwen/Qwen3-Embedding-0.6B",
            embedding_dim=embedding_dim or None,
            use_flash_attention=_get_bool("AML_USE_FLASH_ATTENTION", False),
            generate_sparse_embedding=_get_bool("AML_GENERATE_SPARSE_EMBEDDING", False),
            backend=(os.getenv("AML_BACKEND", "shared") or "shared").strip().lower(),
            retrieval_mode=(os.getenv("AML_RETRIEVAL_MODE", "graph") or "graph").strip().lower(),
            retrieval_methods=_get_list("AML_RETRIEVAL_METHODS", ["cosine", "bm25"]),
            rerank_method=os.getenv("AML_RERANK_METHOD") or None,
            warmup_on_start=_get_bool("AML_WARMUP_ON_START", True),
            l2_dir=os.getenv("AML_L2_DIR") or None,
            max_units_per_user=_get_int("AML_MAX_UNITS_PER_USER", 0) or None,
            data_ttl_days=_get_int("AML_DATA_TTL_DAYS", 30),
            retention_interval_seconds=_get_int("AML_RETENTION_INTERVAL_SECONDS", 3600),
            rate_limit_rpm=_get_int("AML_RATE_LIMIT_RPM", 0),
            add_timeout_seconds=_get_float("AML_ADD_TIMEOUT_SECONDS", 60.0),
            search_timeout_seconds=_get_float("AML_SEARCH_TIMEOUT_SECONDS", 30.0),
            high_level_memory=_get_bool("AML_HIGH_LEVEL_MEMORY", False),
            high_level_debounce_seconds=_get_float("AML_HIGH_LEVEL_DEBOUNCE_SECONDS", 5.0),
            high_level_wait_on_search_seconds=_get_float("AML_HIGH_LEVEL_WAIT_ON_SEARCH_SECONDS", 0.0),
            log_level=(os.getenv("AML_LOG_LEVEL", "INFO") or "INFO").upper(),
        )
        if s.backend not in {"shared", "isolated"}:
            s.backend = "shared"
        if s.retrieval_mode not in {"graph", "hybrid"}:
            s.retrieval_mode = "graph"
        if s.backend == "shared":
            # MultiRetriever is not MemorySpace-scoped, so hybrid retrieval is
            # only safe with per-user isolation.
            s.retrieval_mode = "graph"
        return s
