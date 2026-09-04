"""Optional high-level memory construction (experimental, disabled by default).

Mandol's paper-strength pipeline upgrades base (L0) conversation units into
hierarchical summaries, episodic facts and entity-relation structures that link
back to L0 evidence (see ``mandol.auto_builder`` and Mandol's
``benchmark_self_host`` workflow). This module optionally runs that upgrade for
a user after their Add stream, in a background thread.

It is **off by default** because it requires an LLM provider key (set through
Mandol's environment template, e.g. ``DEEPSEEK_API_KEY`` / ``DASHSCOPE_API_KEY``
/ ``CLOSEAI_API_KEY``) and adds latency. It is recommended only with the
``isolated`` backend and only after a successful smoke test on your own
infrastructure. See docs/03_接口与运行说明.md for guidance.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, List, Optional

from .config import Settings

logger = logging.getLogger("mandol_aml.high_level")

_build_states: dict = {}
_build_states_lock = threading.Lock()


def _env_model(name: str, default: Optional[str]) -> Optional[str]:
    value = os.getenv(name)
    return (value or default) if value or default else None


def schedule_high_level_build(memory_service: Any, state: Any, units: List[Any], settings: Settings) -> None:
    """Start (or postpone) a debounced high-level build for one user."""
    if settings.backend != "isolated":
        logger.warning(
            "AML_HIGH_LEVEL_MEMORY is enabled but backend is not 'isolated'; "
            "high-level memory is skipped (use AML_BACKEND=isolated)."
        )
        return
    extraction_model = _env_model("AML_HLM_EXTRACTION_MODEL", "qwen-3.5-plus-thinking")
    if not extraction_model:
        logger.info("high-level memory skipped: no AML_HLM_EXTRACTION_MODEL set")
        return

    with _build_states_lock:
        info = _build_states.get(state.user_id)
        now = time.time()
        if info is not None and (now - info["last_schedule"]) < settings.high_level_debounce_seconds:
            info["last_schedule"] = now  # postpone
            return
        info = {"last_schedule": now, "thread": None, "finished": True}
        _build_states[state.user_id] = info

    def _run() -> None:
        try:
            time.sleep(settings.high_level_debounce_seconds)
            _do_build(memory_service, state, settings, extraction_model)
        except Exception as exc:  # pragma: no cover
            logger.warning("high-level build failed for user %s: %s", state.user_id, exc)
        finally:
            with _build_states_lock:
                info = _build_states.get(state.user_id)
                if info is not None:
                    info["finished"] = True

    with _build_states_lock:
        _build_states[state.user_id]["thread"] = threading.Thread(
            target=_run, name=f"hlm-{state.user_id[:12]}", daemon=True
        )
        _build_states[state.user_id]["finished"] = False
        _build_states[state.user_id]["thread"].start()


def _do_build(memory_service: Any, state: Any, settings: Settings, extraction_model: str) -> None:
    graph = state.graph
    if graph is None:
        return
    dedup_model = _env_model("AML_HLM_DEDUP_MODEL", "deepseek-v3.2-dashscope")
    l0_units = memory_service.l0_units_for(state)
    if not l0_units:
        return

    try:
        from mandol.auto_builder import build_high_level_memory
        from mandol.llm import LLMClient

        llm_client = LLMClient(model_name=extraction_model)
        dedup_client: Any = None
        if dedup_model:
            try:
                dedup_client = LLMClient(model_name=dedup_model)
            except Exception:
                dedup_client = None
        result = build_high_level_memory(
            semantic_graph=graph,
            l0_units=l0_units,
            llm_client=llm_client,
            dedup_llm_client=dedup_client,
            config=None,
        )
        logger.info(
            "high-level memory built for user %s (l0=%d)",
            state.user_id,
            len(l0_units),
        )
        state.dirty_high_level = False
        del result
    except Exception as exc:
        logger.warning("high-level memory build skipped for user %s: %s", state.user_id, exc)


def wait_for_pending_build(memory_service: Any, state: Any, timeout: float) -> None:
    """Best-effort wait for a pending high-level build.

    ``timeout <= 0`` (default) returns immediately. Note the search path holds
    the service lock while this runs, so a running build cannot be joined from
    here without risking a deadlock; we therefore only wait when the build has
    already finished, which keeps behaviour safe.
    """
    if timeout <= 0:
        return
    with _build_states_lock:
        info = _build_states.get(state.user_id)
        if info is None or info["finished"]:
            return
    # Build is still in progress and the service lock is held by the caller;
    # do not block - retrieve from whatever is already searchable.
    return
