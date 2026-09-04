"""Small in-process sliding-window rate limiter.

AML asks participants to declare their capacity and rate limits. This limiter
exposes a configurable requests-per-minute budget (``AML_RATE_LIMIT_RPM``).
Responses over the budget return HTTP 429 with a Retry-After header, which AML
retries with bounded backoff.
"""

from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self, rpm: int = 0) -> None:
        self.rpm = max(0, int(rpm))
        self._lock = threading.Lock()
        self._window_start = time.monotonic()
        self._count = 0

    @property
    def enabled(self) -> bool:
        return self.rpm > 0

    def allow(self) -> bool:
        """Return True if a request is within the current rate budget."""
        if not self.enabled:
            return True
        now = time.monotonic()
        with self._lock:
            if now - self._window_start >= 60.0:
                self._window_start = now
                self._count = 0
            if self._count < self.rpm:
                self._count += 1
                return True
            return False
