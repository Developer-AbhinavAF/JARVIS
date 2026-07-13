from __future__ import annotations

import time
import logging
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """Runs periodic tasks in the background without blocking requests."""

    def __init__(self) -> None:
        self._tasks: dict[str, tuple[float, Callable[[], None], threading.Thread | None]] = {}
        self._running = False
        self._lock = threading.Lock()

    def add_task(self, name: str, interval: float, func: Callable[[], None]) -> None:
        with self._lock:
            self._tasks[name] = (interval, func, None)

    def remove_task(self, name: str) -> None:
        with self._lock:
            self._tasks.pop(name, None)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True, name="router-scheduler")
        thread.start()
        logger.info("Background scheduler started")

    def stop(self) -> None:
        self._running = False
        logger.info("Background scheduler stopped")

    def _run_loop(self) -> None:
        last_run: dict[str, float] = {}
        while self._running:
            now = time.time()
            with self._lock:
                tasks = dict(self._tasks)
            for name, (interval, func, _) in tasks.items():
                last = last_run.get(name, 0.0)
                if now - last >= interval:
                    try:
                        func()
                        last_run[name] = now
                    except Exception as exc:
                        logger.warning("Scheduled task %s failed: %s", name, exc)
                    last_run[name] = now
            time.sleep(1)

    @property
    def task_count(self) -> int:
        return len(self._tasks)
