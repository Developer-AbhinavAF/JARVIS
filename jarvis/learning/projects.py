"""Project Learning — Maintains project context.

Every project should maintain:
  Goals, Architecture, Dependencies, Recent Files, Bugs,
  TODOs, Ideas, Notes, Progress
Projects become long-term memories.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """A learned project context."""
    project_id: str = ""
    name: str = ""
    path: str = ""
    description: str = ""
    goals: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    recent_files: list[str] = field(default_factory=list)
    bugs: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    ideas: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    progress: float = 0.0        # 0.0-1.0
    last_active: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    interaction_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "languages": self.languages,
            "goals": self.goals,
            "todos": self.todos,
            "progress": self.progress,
            "interaction_count": self.interaction_count,
        }


class ProjectLearner:
    """Learns and maintains project context."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._current_project: str = ""
        self._proj_counter: int = 0

    def track(self, project_name: str, path: str = "", **kwargs: Any) -> Project:
        """Track or update a project."""
        key = project_name.lower()
        if key in self._projects:
            proj = self._projects[key]
            proj.interaction_count += 1
            proj.last_active = time.time()
            for field_name in ("goals", "bugs", "todos", "ideas", "notes", "recent_files"):
                if field_name in kwargs:
                    new_items = kwargs[field_name]
                    if isinstance(new_items, list):
                        getattr(proj, field_name).extend(new_items)
                    else:
                        getattr(proj, field_name).append(str(new_items))
                    # Deduplicate keeping order
                    existing = getattr(proj, field_name)
                    seen: set[str] = set()
                    deduped: list[str] = []
                    for item in existing:
                        if item not in seen:
                            seen.add(item)
                            deduped.append(item)
                    setattr(proj, field_name, deduped[-50:])
            if "languages" in kwargs:
                for lang in kwargs["languages"]:
                    if lang not in proj.languages:
                        proj.languages.append(lang)
            if "progress" in kwargs:
                proj.progress = kwargs["progress"]
        else:
            self._proj_counter += 1
            proj = Project(
                project_id=f"proj_{self._proj_counter:04d}",
                name=project_name,
                path=path,
                description=kwargs.get("description", ""),
                languages=kwargs.get("languages", []),
                goals=kwargs.get("goals", []),
            )
            self._projects[key] = proj

        self._current_project = key
        return proj

    def get_project(self, name: str) -> dict[str, Any] | None:
        proj = self._projects.get(name.lower())
        return proj.to_dict() if proj else None

    def get_current(self) -> dict[str, Any] | None:
        if self._current_project:
            return self._projects[self._current_project].to_dict()
        return None

    def list_projects(self) -> list[dict[str, Any]]:
        return sorted(
            [p.to_dict() for p in self._projects.values()],
            key=lambda p: -p["interaction_count"],
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_projects": len(self._projects),
            "current_project": self._current_project,
        }


project_learner = ProjectLearner()

__all__ = ["ProjectLearner", "Project", "project_learner"]
