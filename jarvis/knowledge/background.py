"""Background Learning — Async learning from various sources.

Supported: YouTube, GitHub, PDF, Folders, Playlists, Repositories, Books, Documentation

Learning should happen asynchronously.
UI Example:
  Learning Python Playlist...
  Progress: 42%
  Current Video: 12/38
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LearningStatus(Enum):
    IDLE = "idle"
    LEARNING = "learning"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LearningTask:
    """A background learning task."""
    task_id: str = ""
    source: str = ""
    source_type: str = ""       # youtube, github, pdf, folder, etc.
    status: LearningStatus = LearningStatus.IDLE
    progress: float = 0.0       # 0.0 - 1.0
    current_item: str = ""
    total_items: int = 0
    completed_items: int = 0
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    result: dict[str, Any] = field(default_factory=dict)


class BackgroundLearner:
    """Manages background learning tasks.

    Learning runs in background threads without blocking the main conversation.
    """

    def __init__(self, max_concurrent: int = 2) -> None:
        self._max_concurrent = max_concurrent
        self._tasks: dict[str, LearningTask] = {}
        self._active_threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._total_learned: int = 0

    @property
    def active_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status == LearningStatus.LEARNING)

    def learn(
        self,
        source: str,
        source_type: str = "text",
        callback: Callable[[LearningTask], None] | None = None,
    ) -> LearningTask:
        """Start a background learning task."""
        import uuid
        task = LearningTask(
            task_id=str(uuid.uuid4())[:8],
            source=source,
            source_type=source_type,
            status=LearningStatus.LEARNING,
            started_at=time.time(),
        )
        self._tasks[task.task_id] = task

        thread = threading.Thread(
            target=self._learn_worker,
            args=(task, callback),
            daemon=True,
            name=f"learn-{task.task_id}",
        )
        self._active_threads.append(thread)
        thread.start()

        return task

    def get_task(self, task_id: str) -> LearningTask | None:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[LearningTask]:
        return list(self._tasks.values())

    def get_active_tasks(self) -> list[LearningTask]:
        return [t for t in self._tasks.values() if t.status == LearningStatus.LEARNING]

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status == LearningStatus.LEARNING:
            task.status = LearningStatus.FAILED
            task.error = "Cancelled by user"
            return True
        return False

    def _learn_worker(self, task: LearningTask, callback: Callable | None) -> None:
        """Background worker for learning."""
        try:
            from .ingestion import ingestion_pipeline

            if task.source_type == "text":
                result = ingestion_pipeline.ingest_text(
                    task.source,
                    source_type="text",
                    source_name="background_learn",
                )
                task.result = {
                    "entities": result.entities_created,
                    "relationships": result.relationships_created,
                }
                task.progress = 1.0

            elif task.source_type == "document":
                from .sources.handlers import document_handler
                doc = document_handler.process(task.source)
                if doc.success:
                    result = ingestion_pipeline.ingest_chunks(
                        doc.chunks,
                        source_type="document",
                        source_name=doc.title,
                    )
                    task.result = {
                        "entities": result.entities_created,
                        "title": doc.title,
                    }
                    task.progress = 1.0
                else:
                    task.error = doc.error

            elif task.source_type == "youtube":
                from .sources.handlers import youtube_handler
                yt = youtube_handler.process(task.source)
                if yt.success:
                    result = ingestion_pipeline.ingest_chunks(
                        yt.chunks,
                        source_type="youtube",
                        source_name=yt.title,
                    )
                    task.result = {"entities": result.entities_created}
                    task.progress = 1.0
                else:
                    task.error = yt.error

            elif task.source_type == "github":
                from .sources.handlers import github_handler
                gh = github_handler.process(task.source)
                if gh.success:
                    result = ingestion_pipeline.ingest_chunks(
                        gh.chunks,
                        source_type="github",
                        source_name=gh.title,
                    )
                    task.result = {"entities": result.entities_created}
                    task.progress = 1.0
                else:
                    task.error = gh.error

            else:
                task.error = f"Unknown source type: {task.source_type}"

            if task.error:
                task.status = LearningStatus.FAILED
            else:
                task.status = LearningStatus.COMPLETED
                self._total_learned += 1

        except Exception as e:
            task.status = LearningStatus.FAILED
            task.error = str(e)
            logger.error("Background learning failed: %s", e)

        task.completed_at = time.time()

        if callback:
            try:
                callback(task)
            except Exception:
                pass

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_tasks": len(self._tasks),
            "active_tasks": self.active_count,
            "completed": sum(1 for t in self._tasks.values() if t.status == LearningStatus.COMPLETED),
            "failed": sum(1 for t in self._tasks.values() if t.status == LearningStatus.FAILED),
            "total_learned": self._total_learned,
        }


background_learner = BackgroundLearner()

__all__ = ["BackgroundLearner", "LearningTask", "LearningStatus", "background_learner"]
