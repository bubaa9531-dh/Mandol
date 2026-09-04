"""Retention janitor: purge evaluation memory after the AML 30-day window."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .config import Settings

logger = logging.getLogger("mandol_aml.retention")


class RetentionJanitor:
    """Periodically delete memory of users that have been idle too long.

    AML requires that evaluation data and derived copies are deleted within 30
    days after a run unless another retention period is approved in writing.
    The janitor enforces that by default (``AML_DATA_TTL_DAYS=30``).
    """

    def __init__(self, memory_service: Any, settings: Settings) -> None:
        self._memory = memory_service
        self._ttl_days = max(1.0, float(settings.data_ttl_days))
        self._interval = max(30.0, float(settings.retention_interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="aml-retention", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                purged = self._memory.purge_idle(self._ttl_days)
                if purged:
                    logger.info("retention janitor purged %d idle user(s)", purged)
            except Exception:
                logger.exception("retention janitor iteration failed")
