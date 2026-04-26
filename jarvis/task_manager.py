"""jarvis.task_manager

Multi-tasking and background task management for JARVIS.
Allows concurrent execution of learning tasks while maintaining chat responsiveness.
"""

import asyncio
import threading
import uuid
import logging
from typing import Dict, Callable, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a background task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a background task."""
    task_id: str
    task_type: str
    description: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "metadata": self.metadata,
        }


class TaskManager:
    """Manages background tasks for JARVIS."""
    
    def __init__(self, max_workers: int = 3):
        """Initialize task manager.
        
        Args:
            max_workers: Maximum concurrent background tasks
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="jarvis_task_")
        self.tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._running = True
        
        # Callbacks for task events
        self._on_complete: Dict[str, List[Callable]] = {}
        self._on_progress: Dict[str, List[Callable]] = {}
        
        logger.info(f"TaskManager initialized with {max_workers} workers")
    
    def submit_task(
        self,
        task_type: str,
        description: str,
        func: Callable,
        *args,
        immediate_response: str = "",
        **kwargs
    ) -> Tuple[str, str]:
        """Submit a task to run in background.
        
        Args:
            task_type: Type of task (youtube_learn, web_search, etc.)
            description: Human-readable description
            func: Function to execute
            args, kwargs: Arguments for function
            immediate_response: Response to return immediately
            
        Returns:
            Tuple of (task_id, immediate_response_message)
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            description=description,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
        )
        
        with self._lock:
            self.tasks[task_id] = task
        
        # Submit to executor
        future = self.executor.submit(self._run_task, task_id, func, *args, **kwargs)
        
        # Add callback for completion
        future.add_done_callback(lambda f: self._handle_completion(task_id, f))
        
        # Generate response message
        if not immediate_response:
            immediate_response = f"⏳ Started {description} in background (Task: {task_id}). You can continue chatting!"
        
        logger.info(f"Task {task_id} submitted: {description}")
        return task_id, immediate_response
    
    def _run_task(self, task_id: str, func: Callable, *args, **kwargs):
        """Execute task with proper state management."""
        with self._lock:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found")
                return
            
            task = self.tasks[task_id]
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
        
        try:
            logger.info(f"Task {task_id} running...")
            
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                # Run async function in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(func(*args, **kwargs))
                loop.close()
            else:
                # Run sync function
                result = func(*args, **kwargs)
            
            with self._lock:
                task = self.tasks[task_id]
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.progress = 100.0
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            with self._lock:
                task = self.tasks[task_id]
                task.error = str(e)
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
    
    def _handle_completion(self, task_id: str, future: Future):
        """Handle task completion."""
        with self._lock:
            if task_id in self._on_complete:
                task = self.tasks.get(task_id)
                for callback in self._on_complete[task_id]:
                    try:
                        callback(task)
                    except Exception as e:
                        logger.error(f"Callback error for task {task_id}: {e}")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks, optionally filtered by status."""
        with self._lock:
            tasks = list(self.tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def get_active_tasks(self) -> List[Task]:
        """Get currently running or pending tasks."""
        return self.get_all_tasks(status=TaskStatus.RUNNING) + self.get_all_tasks(status=TaskStatus.PENDING)
    
    def update_progress(self, task_id: str, progress: float, message: str = ""):
        """Update task progress (0-100)."""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].progress = min(100.0, max(0.0, progress))
                if message:
                    self.tasks[task_id].metadata["progress_message"] = message
        
        # Notify progress callbacks
        if task_id in self._on_progress:
            for callback in self._on_progress[task_id]:
                try:
                    callback(progress, message)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                logger.info(f"Task {task_id} cancelled")
                return True
            return False
    
    def register_callback(self, task_id: str, on_complete: Optional[Callable] = None, on_progress: Optional[Callable] = None):
        """Register callbacks for task events."""
        with self._lock:
            if on_complete:
                if task_id not in self._on_complete:
                    self._on_complete[task_id] = []
                self._on_complete[task_id].append(on_complete)
            
            if on_progress:
                if task_id not in self._on_progress:
                    self._on_progress[task_id] = []
                self._on_progress[task_id].append(on_progress)
    
    def get_status_summary(self) -> str:
        """Get a summary of all tasks."""
        all_tasks = self.get_all_tasks()
        if not all_tasks:
            return "No background tasks."
        
        running = len([t for t in all_tasks if t.status == TaskStatus.RUNNING])
        pending = len([t for t in all_tasks if t.status == TaskStatus.PENDING])
        completed = len([t for t in all_tasks if t.status == TaskStatus.COMPLETED])
        failed = len([t for t in all_tasks if t.status == TaskStatus.FAILED])
        
        return f"Tasks: {running} running, {pending} pending, {completed} completed, {failed} failed"
    
    def shutdown(self):
        """Shutdown task manager gracefully."""
        logger.info("Shutting down TaskManager...")
        self._running = False
        
        # Cancel all pending tasks
        for task in self.get_all_tasks():
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                self.cancel_task(task.task_id)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        logger.info("TaskManager shutdown complete")


# Global task manager instance
task_manager = TaskManager(max_workers=3)


def submit_background_task(
    task_type: str,
    description: str,
    func: Callable,
    *args,
    **kwargs
) -> Tuple[str, str]:
    """Submit a background task."""
    return task_manager.submit_task(task_type, description, func, *args, **kwargs)


def get_task_status(task_id: str) -> Optional[Task]:
    """Get task status."""
    return task_manager.get_task(task_id)


def tool_submit_task(task_type: str, description: str) -> str:
    """Tool: Submit a background task (placeholder for LLM)."""
    return f"Task type '{task_type}' registered: {description}"


def tool_get_task_status(task_id: str) -> str:
    """Tool: Get task status."""
    task = get_task_status(task_id)
    if not task:
        return f"Task {task_id} not found."
    
    status = f"Task {task_id}: {task.status.value}"
    if task.progress > 0:
        status += f" ({task.progress:.0f}%)"
    if task.error:
        status += f" - Error: {task.error}"
    return status


def tool_list_tasks() -> str:
    """Tool: List all tasks."""
    tasks = task_manager.get_all_tasks()
    if not tasks:
        return "No tasks found."
    
    lines = ["Active Tasks:"]
    for task in tasks[:10]:  # Show last 10
        lines.append(f"  {task.task_id}: {task.description} - {task.status.value}")
    return "\n".join(lines)


TASK_REGISTRY = {
    "task_submit": tool_submit_task,
    "task_status": tool_get_task_status,
    "task_list": tool_list_tasks,
}
