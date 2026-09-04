#!/usr/bin/env python3
"""Local AML contract smoke test for the Mandol-AML server.

Run this against a deployed instance to verify the synchronous Add -> Search
flow exactly as the AML platform will exercise it:

    python scripts/smoke_test.py --base-url http://127.0.0.1:8000

Optional environment variables:

    AML_MEMORY_SYSTEM_KEY   the Memory System Key if the API requires auth
    AML_SMOKE_USER_ID       override the default test user id

The script exits 0 only if every contract check passes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid


def _headers(api_key: str) -> dict:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _request(base: str, path: str, api_key: str, payload=None, timeout: float = 30.0):
    url = base.rstrip("/") + path
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(api_key), method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    print(f"ok  : {msg}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("AML_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--key", default=os.getenv("AML_MEMORY_SYSTEM_KEY", ""))
    parser.add_argument("--health-timeout", type=float, default=600.0)
    args = parser.parse_args()

    print(f"Testing {args.base_url}")

    # 1) Health must eventually return 2xx (server warms up the embedding model).
    health_ok = False
    deadline = time.time() + args.health_timeout
    while time.time() < deadline:
        try:
            status, body = _request(args.base_url, "/health", args.key, timeout=10)
            if 200 <= status < 300:
                check(True, f"health returns {status}")
                health_ok = True
                break
        except Exception:
            pass
        time.sleep(5)
    if not health_ok:
        check(False, "health did not become ready in time")

    run_id = f"smoke_{uuid.uuid4().hex[:8]}"
    user_id = os.getenv("AML_SMOKE_USER_ID", f"eval:{run_id}:smoke:user-0")
    session_id = f"eval:{run_id}:sample:0"

    # 2) Add a small memory chunk (contract-shaped payload).
    request_id = f"eval:{run_id}:locomo_refined:conv-0:chunk-0"
    add_payload = {
        "request_id": request_id,
        "messages": [
            {"role": "user", "timestamp": 1704067200000, "content": "Zhang San travelled to Beijing on 2026-06-21 and prefers quiet hotels."},
            {"role": "assistant", "timestamp": 1704067260000, "content": "Got it. I will remember that."},
        ],
        "user_id": user_id,
        "session_id": session_id,
    }
    status, body = _request(args.base_url, "/add", args.key, add_payload)
    check(status == 200, f"add returns HTTP 200 (got {status})")
    check(body.get("success") is True, "add response success == true")
    check(body.get("request_id") == request_id, "add echoes request_id byte-for-byte")
    check(body.get("user_id") == user_id, "add echoes user_id byte-for-byte")
    check(body.get("session_id") == session_id, "add echoes session_id byte-for-byte")

    # 3) Search must return ordered evidence with id + content, within top_k.
    search_payload = {"query": "Where did Zhang San travel and what hotel does he prefer?", "user_id": user_id, "top_k": 10}
    status, body = _request(args.base_url, "/search", args.key, search_payload)
    check(status == 200, f"search returns HTTP 200 (got {status})")
    check(isinstance(body.get("data"), list), "search response contains a data array")
    data = body.get("data", [])
    check(len(data) <= search_payload["top_k"], "search result count within top_k")
    for item in data:
        check(isinstance(item.get("id"), str) and item["id"], "each hit has a non-empty id")
        check(isinstance(item.get("content"), str) and item["content"], "each hit has non-empty content")
    check(len(data) > 0, "search returned at least one relevant memory")

    print(f"\nSmoke test PASSED ({len(data)} hits). Base URL: {args.base_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
