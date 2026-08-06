"""core/background_workers.py — Asynchronous Background Workers for JARVIS vNext++.

Moves heavy operations off the main thread:
- Embedding generation
- OCR processing
- Knowledge & Memory indexing
- Food prompt compilation
- Conversation summarization
- Cache cleanup
- Learning pattern updates
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any

logger = logging.getLogger(__name__)


class BackgroundWorkerPool:
    """ThreadPool background execution engine."""

    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="jarvis_worker")

    def submit_task(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Submit job to background worker thread non-blockingly."""
        def wrapper():
            try:
                fn(*args, **kwargs)
            except Exception as e:
                logger.error(f"Background task error in {fn.__name__}: {e}")

        self._executor.submit(wrapper)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


background_workers = BackgroundWorkerPool()
