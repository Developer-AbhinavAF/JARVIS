"""Project Manager — Long-term project tracking.

Support projects lasting weeks or months.
Store:
- Current Progress
- Completed Tasks
- Pending Tasks
- Deadlines
- Resources
- Documents
- Knowledge

Each project maintains:
- Architecture
- Goals
- Dependencies
- Current Stage
- Recent Changes
- Known Bugs
- Ideas
- Documentation
- Future Plans

Resume exactly where work stopped.
"""

from __future__ import annotations

import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_PROJECTS_FILE = _DATA_DIR / "projects.json"


# ════════════════════════════════════════════════════════════════════
# PROJECT
# ════════════════════════════════════════════════════════════════════

class ProjectStage:
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class ProjectTask:
    """A task within a project."""
    task_id: str = ""
    title: str = ""
    description: str = ""
    status: str = "pending"        # pending, in_progress, done, blocked
    priority: str = "normal"
    assignee: str = "jarvis"
    created_at: float = 0.0
    completed_at: float = 0.0
    tags: list[str] = field(default_factory=list)


@dataclass
class Project:
    """A long-term project."""
    project_id: str = ""
    name: str = ""
    description: str = ""

    # Goals
    goals: list[str] = field(default_factory=list)
    current_stage: str = ProjectStage.PLANNING

    # Tasks
    tasks: list[ProjectTask] = field(default_factory=list)
    completed_tasks: list[ProjectTask] = field(default_factory=list)

    # Architecture & Structure
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    file_structure: dict[str, Any] = field(default_factory=dict)

    # Knowledge
    architecture_notes: str = ""
    recent_changes: list[str] = field(default_factory=list)
    known_bugs: list[str] = field(default_factory=list)
    ideas: list[str] = field(default_factory=list)
    documentation: str = ""
    future_plans: list[str] = field(default_factory=list)

    # Timeline
    deadline: float = 0.0
    created_at: float = 0.0
    updated_at: float = 0.0
    last_accessed: float = 0.0

    # Metadata
    root_path: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = time.time()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    @property
    def progress(self) -> float:
        """Completion percentage 0-1."""
        total = len(self.tasks) + len(self.completed_tasks)
        if total == 0:
            return 0.0
        return len(self.completed_tasks) / total

    @property
    def pending_tasks(self) -> list[ProjectTask]:
        return [t for t in self.tasks if t.status != "done"]

    @property
    def active_tasks(self) -> list[ProjectTask]:
        return [t for t in self.tasks if t.status == "in_progress"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "stage": self.current_stage,
            "progress": round(self.progress, 3),
            "tasks_pending": len(self.pending_tasks),
            "tasks_completed": len(self.completed_tasks),
            "goals": self.goals,
            "languages": self.languages,
            "known_bugs": len(self.known_bugs),
            "ideas": len(self.ideas),
        }


# ════════════════════════════════════════════════════════════════════
# PROJECT MANAGER
# ════════════════════════════════════════════════════════════════════

class ProjectManager:
    """Manages long-term projects.

    Each project maintains its own task list, knowledge base,
    and progress tracking. Projects persist across sessions.
    """

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._active_project: str | None = None
        self._load()

    def create_project(
        self,
        name: str,
        description: str = "",
        root_path: str = "",
        goals: list[str] | None = None,
    ) -> Project:
        """Create a new project."""
        import uuid
        project = Project(
            project_id=f"proj_{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            root_path=root_path,
            goals=goals or [],
        )
        self._projects[project.project_id] = project
        self._active_project = project.project_id
        self._save()
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def get_active_project(self) -> Project | None:
        if self._active_project:
            return self._projects.get(self._active_project)
        return None

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def add_task(self, project_id: str, title: str, description: str = "") -> ProjectTask | None:
        """Add a task to a project."""
        project = self._projects.get(project_id)
        if not project:
            return None
        import uuid
        task = ProjectTask(
            task_id=f"ptask_{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            created_at=time.time(),
        )
        project.tasks.append(task)
        project.updated_at = time.time()
        self._save()
        return task

    def complete_task(self, project_id: str, task_id: str) -> bool:
        """Mark a project task as completed."""
        project = self._projects.get(project_id)
        if not project:
            return False
        for i, task in enumerate(project.tasks):
            if task.task_id == task_id:
                task.status = "done"
                task.completed_at = time.time()
                project.completed_tasks.append(project.tasks.pop(i))
                project.updated_at = time.time()
                self._save()
                return True
        return False

    def add_knowledge(
        self,
        project_id: str,
        architecture: str = "",
        recent_changes: list[str] | None = None,
        known_bugs: list[str] | None = None,
        ideas: list[str] | None = None,
    ) -> bool:
        """Update project knowledge base."""
        project = self._projects.get(project_id)
        if not project:
            return False
        if architecture:
            project.architecture_notes = architecture
        if recent_changes:
            project.recent_changes.extend(recent_changes)
            project.recent_changes = project.recent_changes[-20:]
        if known_bugs:
            project.known_bugs.extend(known_bugs)
        if ideas:
            project.ideas.extend(ideas)
        project.updated_at = time.time()
        self._save()
        return True

    def resume_project(self, project_id: str) -> dict[str, Any] | None:
        """Get project state for resumption."""
        project = self._projects.get(project_id)
        if not project:
            return None
        project.last_accessed = time.time()
        self._active_project = project_id
        self._save()
        return {
            "project": project.to_dict(),
            "pending_tasks": [t.title for t in project.pending_tasks],
            "active_tasks": [t.title for t in project.active_tasks],
            "known_bugs": project.known_bugs,
            "recent_changes": project.recent_changes[-5:],
            "next_steps": project.future_plans[:3] if project.future_plans else [],
        }

    def _save(self) -> None:
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "active_project": self._active_project,
                "projects": {
                    pid: {
                        **p.to_dict(),
                        "architecture_notes": p.architecture_notes,
                        "recent_changes": p.recent_changes,
                        "known_bugs": p.known_bugs,
                        "ideas": p.ideas,
                        "future_plans": p.future_plans,
                        "tasks": [
                            {"task_id": t.task_id, "title": t.title,
                             "description": t.description, "status": t.status}
                            for t in p.tasks
                        ],
                        "completed_tasks": [
                            {"task_id": t.task_id, "title": t.title}
                            for t in p.completed_tasks
                        ],
                    }
                    for pid, p in self._projects.items()
                },
                "saved_at": time.time(),
            }
            _PROJECTS_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("Failed to save projects: %s", e)

    def _load(self) -> None:
        try:
            if _PROJECTS_FILE.exists():
                data = json.loads(_PROJECTS_FILE.read_text())
                self._active_project = data.get("active_project")
                for pid, pdata in data.get("projects", {}).items():
                    project = Project(
                        project_id=pid,
                        name=pdata.get("name", ""),
                        description=pdata.get("description", ""),
                        current_stage=pdata.get("stage", ProjectStage.PLANNING),
                        goals=pdata.get("goals", []),
                        languages=pdata.get("languages", []),
                        architecture_notes=pdata.get("architecture_notes", ""),
                        recent_changes=pdata.get("recent_changes", []),
                        known_bugs=pdata.get("known_bugs", []),
                        ideas=pdata.get("ideas", []),
                        future_plans=pdata.get("future_plans", []),
                    )
                    for t_data in pdata.get("tasks", []):
                        project.tasks.append(ProjectTask(
                            task_id=t_data.get("task_id", ""),
                            title=t_data.get("title", ""),
                            description=t_data.get("description", ""),
                            status=t_data.get("status", "pending"),
                        ))
                    for t_data in pdata.get("completed_tasks", []):
                        project.completed_tasks.append(ProjectTask(
                            task_id=t_data.get("task_id", ""),
                            title=t_data.get("title", ""),
                            status="done",
                        ))
                    self._projects[pid] = project
        except Exception as e:
            logger.debug("Failed to load projects: %s", e)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_projects": len(self._projects),
            "active": sum(1 for p in self._projects.values()
                         if p.current_stage == ProjectStage.ACTIVE),
            "pending_tasks": sum(len(p.pending_tasks) for p in self._projects.values()),
            "completed_tasks": sum(len(p.completed_tasks) for p in self._projects.values()),
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

project_manager = ProjectManager()
