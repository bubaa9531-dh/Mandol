"""Memory System Key authentication for the AML adapter.

AML accepts the ``Token``, ``Bearer`` and ``X-Api-Key`` schemes. When a key is
configured, every Add / Search call must present it. When no key is configured
the endpoints are open - AML permits unauthenticated endpoints only for the
public smoke compatibility check, so set a key before a formal evaluation.
"""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request


def _safe_eq(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def extract_credential(request: Request) -> str:
    """Return the Memory System Key from the request, or an empty string."""
    auth = request.headers.get("authorization", "")
    if auth:
        parts = auth.split(None, 1)
        if len(parts) == 2 and parts[0].lower() in {"bearer", "token"}:
            return parts[1].strip()
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key.strip()
    return ""


def require_auth(request: Request, expected_key: str) -> None:
    """Raise HTTP 401 unless a valid Memory System Key is provided."""
    if not expected_key:
        return
    provided = extract_credential(request)
    if not provided or not _safe_eq(provided, expected_key):
        raise HTTPException(
            status_code=401,
            detail={"reason": "invalid or missing Memory System Key"},
            headers={"WWW-Authenticate": "Bearer"},
        )
