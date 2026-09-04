#!/usr/bin/env python3
"""Local end-to-end connectivity test for Mandol-AML.

Boots the Mandol-AML server (or reuses one already running), then verifies the
synchronous Add -> Search chain exactly like the AML platform will:

    python aml/scripts/run_local_e2e.py            # run from the repo root

Optional flags:
    --repo-dir PATH      repo root (default: current directory)
    --port 8000          server port to use
    --base-url URL       full base url (default http://127.0.0.1:<port>)
    --health-timeout N   seconds to wait for /health (default 1800)
    --keep-running       do not stop the server at the end

Exit code 0 means the whole chain (boot -> health -> Add -> Search -> schema)
passed on the local machine.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


def _request(base: str, path: str, payload=None, timeout: float = 60.0):
    url = base.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    print(f"ok  : {msg}")


def wait_health(base: str, timeout: float) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            status, _ = _request(base, "/health", timeout=10)
            if 200 <= status < 300:
                check(True, f"health returns {status}")
                return
            last = f"status={status}"
        except Exception as exc:  # noqa: BLE001
            last = str(exc)[:120]
        time.sleep(5)
    check(False, f"health not ready in {timeout:.0f}s; last error: {last}")


def run_checks(base: str) -> None:
    run_id = f"e2e_{uuid.uuid4().hex[:8]}"
    user_id = f"eval:{run_id}:locomo:conv-0"
    session_id = f"eval:{run_id}:sample:0"
    request_id = f"eval:{run_id}:locomo_refined:conv-0:chunk-0"

    add_payload = {
        "request_id": request_id,
        "messages": [
            {"role": "user", "timestamp": 1704067200000,
             "content": "Zhang San travelled to Beijing on 2026-06-21 and prefers quiet hotels."},
            {"role": "assistant", "timestamp": 1704067260000,
             "content": "Got it. I will remember that."},
        ],
        "user_id": user_id,
        "session_id": session_id,
    }
    status, body = _request(base, "/add", add_payload)
    check(status == 200, f"add returns HTTP 200 (got {status})")
    check(body.get("success") is True, "add response success == true")
    check(body.get("request_id") == request_id, "add echoes request_id byte-for-byte")
    check(body.get("user_id") == user_id, "add echoes user_id byte-for-byte")
    check(body.get("session_id") == session_id, "add echoes session_id byte-for-byte")

    search_payload = {
        "query": "Where did Zhang San travel and what hotel does he prefer?",
        "user_id": user_id,
        "top_k": 10,
    }
    status, body = _request(base, "/search", search_payload)
    check(status == 200, f"search returns HTTP 200 (got {status})")
    check(isinstance(body.get("data"), list), "search response contains a data array")
    data = body.get("data", [])
    check(len(data) <= search_payload["top_k"], "search result count within top_k")
    for item in data:
        check(isinstance(item.get("id"), str) and item["id"], "each hit has non-empty id")
        check(isinstance(item.get("content"), str) and item["content"], "each hit has non-empty content")
    check(len(data) > 0, "search returned at least one relevant memory")
    print(f"\nE2E PASSED ({len(data)} hits). Base URL: {base}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", default=os.getcwd())
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--health-timeout", type=float, default=1800.0)
    parser.add_argument("--keep-running", action="store_true")
    args = parser.parse_args()

    base = args.base_url or f"http://127.0.0.1:{args.port}"
    env = dict(os.environ)
    env.setdefault("AML_HOST", "127.0.0.1")
    env.setdefault("AML_PORT", str(args.port))

    # If something already answers /health, treat it as an external server.
    try:
        status, _ = _request(base, "/health", timeout=3)
        if 200 <= status < 300:
            print("Reusing an already-running server at", base)
            run_checks(base)
            return 0
    except Exception:
        pass

    print("Starting Mandol-AML server (python -m mandol_aml) ...")
    log = os.path.join(args.repo_dir, "mandol_aml_e2e.log")
    with open(log, "w", encoding="utf-8") as fh:
        proc = subprocess.Popen(
            [sys.executable, "-m", "mandol_aml"],
            cwd=args.repo_dir,
            env=env,
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
    try:
        wait_health(base, args.health_timeout)
        run_checks(base)
    finally:
        if not args.keep_running and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
