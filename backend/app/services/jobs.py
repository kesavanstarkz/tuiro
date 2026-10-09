"""Background Job Runner Interface and Default Implementations."""
from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable

logger = logging.getLogger(__name__)


class JobRunner(ABC):
    @abstractmethod
    def enqueue(self, func: Callable, *args: Any, idempotency_key: str | None = None, **kwargs: Any) -> bool:
        """Enqueue a callable to be run asynchronously."""
        pass

    @abstractmethod
    def run_now(self, func: Callable, *args: Any, idempotency_key: str | None = None, **kwargs: Any) -> Any:
        """Run a callable synchronously."""
        pass


class ThreadJobRunner(JobRunner):
    """In-memory threaded job runner with idempotency tracking."""

    def __init__(self) -> None:
        self._processed_keys: set[str] = set()
        self._lock = threading.Lock()

    def enqueue(self, func: Callable, *args: Any, idempotency_key: str | None = None, **kwargs: Any) -> bool:
        if idempotency_key:
            with self._lock:
                if idempotency_key in self._processed_keys:
                    logger.info("Job with idempotency key %s already processed or in progress; skipping duplicate.", idempotency_key)
                    return False
                self._processed_keys.add(idempotency_key)

        def runner():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error("Background job failed: %s", e, exc_info=True)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        return True

    def run_now(self, func: Callable, *args: Any, idempotency_key: str | None = None, **kwargs: Any) -> Any:
        if idempotency_key:
            with self._lock:
                if idempotency_key in self._processed_keys:
                    logger.info("Job with idempotency key %s already processed; skipping duplicate.", idempotency_key)
                    return None
                self._processed_keys.add(idempotency_key)

        return func(*args, **kwargs)


# Global job runner instance
_default_runner: JobRunner = ThreadJobRunner()


def get_job_runner() -> JobRunner:
    return _default_runner


def set_job_runner(runner: JobRunner) -> None:
    global _default_runner
    _default_runner = runner
