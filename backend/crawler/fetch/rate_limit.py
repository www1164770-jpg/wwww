"""Cancellable process-local global and per-origin request limiting."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import threading
import time

from backend.crawler.errors import Cancelled


class OriginRateLimiter:
    """Serialize each origin while allowing unrelated origins to progress."""

    def __init__(
        self,
        *,
        global_concurrency: int,
        default_delay_seconds: int | float,
        monotonic: Callable[[], float] = time.monotonic,
        wait: Callable[[threading.Event, float], bool] | None = None,
    ) -> None:
        if global_concurrency < 1:
            raise ValueError("global concurrency must be positive")
        if default_delay_seconds <= 0:
            raise ValueError("origin delay must be positive")
        self._global = threading.BoundedSemaphore(global_concurrency)
        self._default_delay = float(default_delay_seconds)
        self._monotonic = monotonic
        self._wait = wait or (lambda event, seconds: event.wait(seconds))
        self._state_lock = threading.Lock()
        self._origin_locks: dict[str, threading.Lock] = {}
        self._last_finished: dict[str, float] = {}

    @staticmethod
    def _acquire_cancellable(
        lock: threading.Lock | threading.Semaphore,
        cancel_event: threading.Event,
    ) -> None:
        while not lock.acquire(timeout=0.2):
            if cancel_event.is_set():
                raise Cancelled()
        if cancel_event.is_set():
            lock.release()
            raise Cancelled()

    @contextmanager
    def slot(
        self,
        origin: str,
        *,
        crawl_delay: int | float | None = None,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[None]:
        event = cancel_event or threading.Event()
        with self._state_lock:
            origin_lock = self._origin_locks.setdefault(origin, threading.Lock())

        self._acquire_cancellable(origin_lock, event)
        global_acquired = False
        try:
            delay = max(
                self._default_delay,
                float(crawl_delay) if crawl_delay is not None else 0.0,
            )
            with self._state_lock:
                last_finished = self._last_finished.get(origin)
            if last_finished is not None:
                remaining = (last_finished + delay) - self._monotonic()
                if remaining > 0 and self._wait(event, remaining):
                    raise Cancelled()
            if event.is_set():
                raise Cancelled()
            self._acquire_cancellable(self._global, event)
            global_acquired = True
            yield
        finally:
            if global_acquired:
                self._global.release()
                with self._state_lock:
                    self._last_finished[origin] = self._monotonic()
            origin_lock.release()
