"""core/skill_manager.py — Workflow Skill System for JARVIS vNext++.

Wraps single tool primitives into reusable multi-step workflow Skills:
Example:
  ResearchAISkill -> Open Browser -> Search -> Read -> Summarize -> Save Notes
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SkillStep:
    tool_name: str
    description: str
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Skill:
    name: str
    description: str
    steps: List[SkillStep] = field(default_factory=list)


class SkillManager:
    """Manages multi-step workflow skills."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._register_default_skills()

    def _register_default_skills(self) -> None:
        # Research AI Skill
        self.register_skill(
            Skill(
                name="ResearchAI",
                description="Search web for AI topics, summarize results, and save notes.",
                steps=[
                    SkillStep(tool_name="web_search", description="Search web for target query"),
                    SkillStep(tool_name="summarize_text", description="Summarize web search results"),
                ],
            )
        )

    def register_skill(self, skill: Skill) -> None:
        self._skills[skill.name.lower()] = skill
        logger.info(f"Registered skill: {skill.name}")

    def find_skill(self, name_or_query: str) -> Optional[Skill]:
        query_clean = name_or_query.lower().strip()
        for name, skill in self._skills.items():
            if name in query_clean or query_clean in skill.description.lower():
                return skill
        return None


skill_manager = SkillManager()
