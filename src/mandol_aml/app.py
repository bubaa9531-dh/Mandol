"""FastAPI application exposing the AML Add / Search / Health contract."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import Settings
from .memory import MemoryService
from .ratelimit import RateLimiter
from .retention import RetentionJanitor
from .schemas import AddRequest, AddResponse, SearchRequest, SearchResponse
from .security import require_auth
from .version import __version__

logger = logging.getLogger("mandol_aml.app")


def _not_ready() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"reason": "memory system is warming up or unavailable"},
    )


def _rate_limited() -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={"reason": "rate limit exceeded"},
        headers={"Retry-After": "60"},
    )


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    cfg = settings or Settings.from_env()
    memory = MemoryService(cfg)
    limiter = RateLimiter(cfg.rate_limit_rpm)
    janitor = RetentionJanitor(memory, cfg)
    ready_event_holder: Dict[str, Any] = {"ready": False, "started": False}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("starting Mandol-AML %s (backend=%s)", __version__, cfg.backend)

        # Mandol warm-up (embedding model download/load) can take minutes on the
        # first start. Run it in a background thread so the HTTP server starts
        # immediately and /health reports 503 until the memory system is ready -
        # this matches the AML health semantics and the Docker HEALTHCHECK.
        def _initialize() -> None:
            try:
                memory.start()
                ready_event_holder["ready"] = True
                logger.info("Mandol runtime is ready")
            except Exception:
                logger.exception("Mandol runtime failed to start; health will report not-ready")
                ready_event_holder["ready"] = False
            finally:
                ready_event_holder["started"] = True

        threading.Thread(target=_initialize, name="aml-init", daemon=True).start()
        janitor.start()
        yield
        janitor.stop()
        # Only purge user memory if initialization finished; otherwise the daemon
        # init thread is still warming up and there is nothing to clean yet.
        if ready_event_holder["started"] and memory.ready:
            try:
                memory.shutdown()
            except Exception:
                logger.exception("error during shutdown")

    app = FastAPI(
        title="Mandol-AML",
        version=__version__,
        description="Agent Memory Leaderboard Add/Search adapter for the Mandol memory system.",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def limit_body_size(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            length = request.headers.get("content-length")
            if length:
                try:
                    if int(length) > cfg.max_request_bytes:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": {"reason": "request body too large"}},
                        )
                except ValueError:
                    pass
        return await call_next(request)

    @app.get(cfg.health_path, include_in_schema=False)
    def health() -> Dict[str, Any]:
        if not ready_event_holder["ready"] or not memory.ready:
            reason = memory.init_error or (
                "memory system is initializing"
                if not ready_event_holder["started"]
                else "memory system is unavailable"
            )
            raise HTTPException(status_code=503, detail={"reason": reason})
        stats = memory.stats()
        return {
            "status": "ok",
            "system": "Mandol-AML",
            "version": __version__,
            "backend": stats["backend"],
            "retrieval_mode": stats["retrieval_mode"],
            "ready": True,
        }

    @app.get("/", include_in_schema=False)
    def root() -> Dict[str, Any]:
        return {
            "system": "Mandol-AML",
            "version": __version__,
            "upstream": "Mandol 0.1.0 (https://github.com/AgentCombo/Mandol)",
            "contract": "https://agentmemoryleaderboard.ai/api-guide",
            "endpoints": {
                "add": cfg.add_path,
                "search": cfg.search_path,
                "health": cfg.health_path,
            },
            "ready": ready_event_holder["ready"] and memory.ready,
        }

    @app.post(cfg.add_path, response_model=AddResponse)
    def add(payload: AddRequest, request: Request) -> AddResponse:
        require_auth(request, cfg.memory_system_key)
        if not limiter.allow():
            raise _rate_limited()
        if not ready_event_holder["ready"] or not memory.ready:
            raise _not_ready()
        memory.add_messages(
            user_id=payload.user_id,
            session_id=payload.session_id,
            request_id=payload.request_id,
            messages=[m.model_dump() for m in payload.messages],
        )
        # Echo the exact identifiers received (contract requirement).
        return AddResponse(
            success=True,
            request_id=payload.request_id,
            user_id=payload.user_id,
            session_id=payload.session_id,
        )

    @app.post(cfg.search_path, response_model=SearchResponse, response_model_exclude_none=True)
    def search(payload: SearchRequest, request: Request) -> SearchResponse:
        require_auth(request, cfg.memory_system_key)
        if not limiter.allow():
            raise _rate_limited()
        if not ready_event_holder["ready"] or not memory.ready:
            raise _not_ready()
        hits = memory.search(
            user_id=payload.user_id,
            query=payload.query,
            top_k=payload.top_k,
        )
        data = [
            {
                "id": hit["id"],
                "content": hit["content"],
                "score": hit["score"],
                "created_at": hit["created_at"],
            }
            for hit in hits
        ]
        return SearchResponse(data=data)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": {"reason": "internal server error"}},
        )

    return app
