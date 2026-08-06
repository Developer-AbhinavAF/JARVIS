"""profiles — Dynamic response profile system for adaptive generation.

Automatically selects profile based on input type and context.
Each profile has specific LLM parameters optimized for that use case.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ProfileType(Enum):
    """Response profile types."""
    FAST = "fast"
    NORMAL = "normal"
    WRITING = "writing"
    CODING = "coding"
    PROJECT = "project"


@dataclass
class Profile:
    """Response profile with LLM parameters."""
    name: str
    think: bool
    temperature: float
    num_predict: int
    use_cases: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    file_by_file: bool = False
    
    def get_llm_params(self) -> Dict[str, Any]:
        """Get LLM parameters for this profile."""
        return {
            "temperature": self.temperature,
            "num_predict": self.num_predict,
            "think": self.think
        }
    
    def matches(self, input: str, context: Dict[str, Any] = None) -> float:
        """Calculate match score for this profile (0.0 to 1.0)."""
        context = context or {}
        input_lower = input.lower().strip()
        score = 0.0
        
        # Check keywords
        for keyword in self.keywords:
            if keyword.lower() in input_lower:
                score += 0.3
        
        # Check patterns
        for pattern in self.patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                score += 0.4
        
        # Check use cases from context
        if context and "intent" in context:
            intent = context["intent"].lower()
            for use_case in self.use_cases:
                if use_case.lower() in intent:
                    score += 0.3
        
        return min(score, 1.0)


class ProfileManager:
    """Manages dynamic profile selection."""
    
    def __init__(self):
        self._profiles = {
            ProfileType.FAST: Profile(
                name="FAST",
                think=False,
                temperature=0.2,
                num_predict=128,
                use_cases=["greeting", "simple_question", "tool_calling", "memory_lookup"],
                keywords=["hello", "hi", "hey", "ok", "yes", "no", "thanks", "bye"],
                patterns=[r"^(hello|hi|hey|ok|yes|no|thanks|bye)", r"\?$"]
            ),
            ProfileType.NORMAL: Profile(
                name="NORMAL",
                think=False,
                temperature=0.5,
                num_predict=512,
                use_cases=["conversation", "general_question", "chat"],
                keywords=["what", "how", "why", "when", "where", "who", "tell", "explain"],
                patterns=[r"^(what|how|why|when|where|who)", r"tell me", r"explain"]
            ),
            ProfileType.WRITING: Profile(
                name="WRITING",
                think=True,
                temperature=0.7,
                num_predict=2048,
                use_cases=["notes", "essay", "documentation", "explanation", "writing"],
                keywords=["write", "note", "document", "essay", "article", "blog", "explain"],
                patterns=[r"^write", r"^create.*note", r"^document", r"^essay"]
            ),
            ProfileType.CODING: Profile(
                name="CODING",
                think=True,
                temperature=0.3,
                num_predict=4096,
                use_cases=["programming", "debugging", "architecture", "projects", "code"],
                keywords=["code", "function", "class", "debug", "fix", "implement", "api", "database"],
                patterns=[r"^code", r"^debug", r"^fix", r"^implement", r"function", r"class"]
            ),
            ProfileType.PROJECT: Profile(
                name="PROJECT",
                think=True,
                temperature=0.5,
                num_predict=8192,
                use_cases=["large_project", "website", "jarvis_module", "app"],
                keywords=["project", "website", "application", "app", "system", "platform"],
                patterns=[r"^create.*project", r"^build.*website", r"^develop.*app"],
                file_by_file=True
            )
        }
        self._default_profile = ProfileType.NORMAL
    
    def select_profile(self, input: str, context: Dict[str, Any] = None) -> Profile:
        """Select best matching profile for input."""
        context = context or {}
        
        # Calculate scores for all profiles
        scores = {}
        for profile_type, profile in self._profiles.items():
            score = profile.matches(input, context)
            scores[profile_type] = score
        
        # Select profile with highest score
        best_profile_type = max(scores, key=scores.get)
        best_score = scores[best_profile_type]
        
        # If no strong match, use default
        if best_score < 0.3:
            best_profile_type = self._default_profile
            logger.debug(f"No strong profile match, using default: {best_profile_type.value}")
        else:
            logger.debug(f"Selected profile: {best_profile_type.value} (score: {best_score:.2f})")
        
        return self._profiles[best_profile_type]
    
    def get_profile(self, profile_type: ProfileType) -> Profile:
        """Get specific profile by type."""
        return self._profiles.get(profile_type, self._profiles[self._default_profile])
    
    def get_all_profiles(self) -> Dict[ProfileType, Profile]:
        """Get all available profiles."""
        return self._profiles.copy()


# Global profile manager instance
profile_manager = ProfileManager()
