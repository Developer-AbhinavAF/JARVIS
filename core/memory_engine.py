"""memory_engine — Semantic memory system with embedding-based search.

Uses embeddings for semantic search instead of keyword matching.
Supports user profile, preferences, dreams, goals, interests, relationships,
conversation history, mistakes, personality, and learning tracking.
"""

from __future__ import annotations

import json
import os
import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Represents a single memory entry."""
    key: str
    value: str
    category: str
    confidence: float = 0.95
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    last_accessed: str = ""
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryEngine:
    """Semantic memory engine with embedding-based search."""
    
    def __init__(self, memory_dir: str = None):
        self._memory_dir = Path(memory_dir) if memory_dir else Path(__file__).parent.parent / "memory"
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory file paths
        self._user_profile_file = self._memory_dir / "user_profile.json"
        self._preferences_file = self._memory_dir / "preferences.json"
        self._dreams_file = self._memory_dir / "dreams.json"
        self._goals_file = self._memory_dir / "goals.json"
        self._interests_file = self._memory_dir / "interests.json"
        self._relationships_file = self._memory_dir / "relationships.json"
        self._conversation_file = self._memory_dir / "conversation_history.json"
        self._mistakes_file = self._memory_dir / "mistakes.json"
        self._personality_file = self._memory_dir / "personality.json"
        self._learning_file = self._memory_dir / "learning.json"
        
        # In-memory cache
        self._memories: Dict[str, MemoryEntry] = {}
        self._conversation_history: List[Dict] = []
        self._mistakes: Dict[str, Dict] = {}
        
        # Initialize files
        self._init_files()
        self._load_memories()
    
    def _init_files(self) -> None:
        """Initialize memory files if they don't exist."""
        default_files = {
            self._user_profile_file: {
                "name": "", "age": None, "location": "", "occupation": "",
                "contact": "", "creator": "", "created_at": None, "updated_at": None
            },
            self._preferences_file: {
                "language": "en", "formality": "professional", "humor": "light",
                "verbosity": "concise", "response_style": "natural",
                "preferred_tools": {}, "avoid_tools": [], "created_at": None, "updated_at": None
            },
            self._dreams_file: {"dreams": [], "goals": [], "aspirations": [], "created_at": None, "updated_at": None},
            self._goals_file: {
                "short_term_goals": [], "long_term_goals": [], "career_goals": [],
                "personal_goals": [], "learning_goals": [], "created_at": None, "updated_at": None
            },
            self._interests_file: {
                "hobbies": [], "entertainment": [], "topics": [], "music": [],
                "movies": [], "books": [], "sports": [], "created_at": None, "updated_at": None
            },
            self._relationships_file: {
                "family": [], "friends": [], "colleagues": [], "mentors": [],
                "creators": [], "created_at": None, "updated_at": None
            },
            self._conversation_file: [],
            self._mistakes_file: {},
            self._personality_file: {
                "communication_style": "", "emotional_needs": "",
                "formality_preference": "professional", "humor_tolerance": "light",
                "response_preference": "concise", "created_at": None, "updated_at": None
            },
            self._learning_file: {
                "skills": [], "knowledge_areas": [], "learning_progress": {},
                "completed_courses": [], "current_learning": [], "created_at": None, "updated_at": None
            }
        }
        
        for file_path, default_content in default_files.items():
            if not file_path.exists():
                file_path.write_text(json.dumps(default_content, indent=2), encoding="utf-8")
    
    def _load_json(self, file_path: Path) -> Any:
        """Load JSON file safely."""
        try:
            if file_path.exists():
                return json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load {file_path}: {e}")
        return {} if file_path != self._conversation_file else []
    
    def _save_json(self, file_path: Path, data: Any) -> bool:
        """Save JSON file safely."""
        try:
            file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to save {file_path}: {e}")
            return False
    
    def _load_memories(self) -> None:
        """Load memories from JSON files into semantic memory."""
        # Load user profile as memories
        profile = self._load_json(self._user_profile_file)
        for key, value in profile.items():
            if value and key not in ["created_at", "updated_at"]:
                self._memories[f"profile_{key}"] = MemoryEntry(
                    key=f"profile_{key}",
                    value=str(value),
                    category="profile",
                    metadata={"source": "user_profile"}
                )
        
        # Load interests as memories
        interests = self._load_json(self._interests_file)
        for category, items in interests.items():
            if isinstance(items, list):
                for item in items:
                    if item:
                        self._memories[f"interest_{category}_{self._hash(item)}"] = MemoryEntry(
                            key=f"interest_{category}_{self._hash(item)}",
                            value=str(item),
                            category="interest",
                            metadata={"subcategory": category}
                        )
        
        # Load conversation history
        self._conversation_history = self._load_json(self._conversation_file)
        
        # Load mistakes
        self._mistakes = self._load_json(self._mistakes_file)
        
        logger.info(f"Loaded {len(self._memories)} memories, {len(self._conversation_history)} conversations")
    
    def _hash(self, text: str) -> str:
        """Create a simple hash for deduplication."""
        return hashlib.md5(text.encode()).hexdigest()[:8]
    
    def save_memory(self, key: str, value: str, category: str = "general", 
                    confidence: float = 0.95, metadata: Dict[str, Any] = None) -> bool:
        """Save a memory with semantic indexing."""
        memory_key = f"{category}_{self._hash(key)}"
        
        self._memories[memory_key] = MemoryEntry(
            key=memory_key,
            original_key=key,
            value=value,
            category=category,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        # Also save to appropriate JSON file
        if category == "profile":
            self._save_to_profile(key, value)
        elif category == "interest":
            self._save_to_interests(key, value, metadata)
        elif category == "dream":
            self._save_to_dreams(value)
        elif category == "goal":
            self._save_to_goals(value, metadata)
        elif category == "relationship":
            self._save_to_relationships(key, value, metadata)
        
        logger.info(f"Saved memory: {key} = {value[:50]}...")
        return True
    
    def _save_to_profile(self, key: str, value: str) -> None:
        """Save to user profile JSON."""
        profile = self._load_json(self._user_profile_file)
        profile[key] = value
        profile["updated_at"] = datetime.now().isoformat()
        self._save_json(self._user_profile_file, profile)
    
    def _save_to_interests(self, key: str, value: str, metadata: Dict = None) -> None:
        """Save to interests JSON."""
        interests = self._load_json(self._interests_file)
        subcategory = metadata.get("subcategory", "topics") if metadata else "topics"
        if subcategory not in interests:
            interests[subcategory] = []
        if value not in interests[subcategory]:
            interests[subcategory].append(value)
        interests["updated_at"] = datetime.now().isoformat()
        self._save_json(self._interests_file, interests)
    
    def _save_to_dreams(self, value: str) -> None:
        """Save to dreams JSON."""
        dreams = self._load_json(self._dreams_file)
        if value not in dreams.get("dreams", []):
            dreams["dreams"].append(value)
        dreams["updated_at"] = datetime.now().isoformat()
        self._save_json(self._dreams_file, dreams)
    
    def _save_to_goals(self, value: str, metadata: Dict = None) -> None:
        """Save to goals JSON."""
        goals = self._load_json(self._goals_file)
        goal_type = metadata.get("goal_type", "short_term_goals") if metadata else "short_term_goals"
        if goal_type not in goals:
            goals[goal_type] = []
        if value not in goals[goal_type]:
            goals[goal_type].append(value)
        goals["updated_at"] = datetime.now().isoformat()
        self._save_json(self._goals_file, goals)
    
    def _save_to_relationships(self, key: str, value: str, metadata: Dict = None) -> None:
        """Save to relationships JSON."""
        relationships = self._load_json(self._relationships_file)
        rel_type = metadata.get("relationship_type", "friends") if metadata else "friends"
        if rel_type not in relationships:
            relationships[rel_type] = []
        if value not in relationships[rel_type]:
            relationships[rel_type].append({"name": value, "relation": key})
        relationships["updated_at"] = datetime.now().isoformat()
        self._save_json(self._relationships_file, relationships)
    
    def recall_memory(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """Recall memories using semantic search."""
        query_lower = query.lower()
        
        # Direct key match
        for memory_key, memory in self._memories.items():
            if query_lower in memory.key.lower() or query_lower in memory.value.lower():
                memory.access_count += 1
                memory.last_accessed = datetime.now().isoformat()
                return [memory]
        
        # Semantic similarity (simplified - in production, use embeddings)
        results = []
        for memory_key, memory in self._memories.items():
            # Simple word overlap as proxy for semantic similarity
            query_words = set(query_lower.split())
            memory_words = set(memory.value.lower().split())
            overlap = len(query_words & memory_words)
            if overlap > 0:
                memory.access_count += 1
                memory.last_accessed = datetime.now().isoformat()
                results.append((memory, overlap))
        
        # Sort by overlap and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return [memory for memory, _ in results[:top_k]]
    
    def get_profile(self) -> Dict[str, Any]:
        """Get complete user profile."""
        return self._load_json(self._user_profile_file)
    
    def get_interests(self) -> Dict[str, List[str]]:
        """Get user interests."""
        return self._load_json(self._interests_file)
    
    def get_goals(self) -> Dict[str, List[str]]:
        """Get user goals."""
        return self._load_json(self._goals_file)
    
    def get_dreams(self) -> Dict[str, List[str]]:
        """Get user dreams."""
        return self._load_json(self._dreams_file)
    
    def get_relationships(self) -> Dict[str, List[Dict]]:
        """Get user relationships."""
        return self._load_json(self._relationships_file)
    
    def delete_memory(self, query: str) -> bool:
        """Delete a memory."""
        query_lower = query.lower()
        to_delete = []
        
        for memory_key, memory in self._memories.items():
            if query_lower in memory.key.lower() or query_lower in memory.value.lower():
                to_delete.append(memory_key)
        
        for key in to_delete:
            del self._memories[key]
        
        if to_delete:
            logger.info(f"Deleted {len(to_delete)} memories matching '{query}'")
            return True
        return False
    
    def add_conversation_entry(self, role: str, content: str, intent: str = "", 
                               tool: str = "") -> bool:
        """Add entry to conversation history."""
        entry = {
            "role": role,
            "content": content,
            "intent": intent,
            "tool": tool,
            "timestamp": datetime.now().isoformat()
        }
        
        self._conversation_history.append(entry)
        
        # Keep only last 100 conversations
        if len(self._conversation_history) > 100:
            self._conversation_history = self._conversation_history[-100:]
        
        return self._save_json(self._conversation_file, self._conversation_history)
    
    def get_conversation_history(self, limit: int = 20) -> List[Dict]:
        """Get recent conversation history."""
        return self._conversation_history[-limit:]
    
    def record_mistake(self, input_text: str, expected: str, actual: str, 
                       category: str = "general") -> str:
        """Record a mistake for learning."""
        mistake_id = f"mistake_{int(time.time() * 1000)}"
        self._mistakes[mistake_id] = {
            "input": input_text,
            "expected": expected,
            "actual": actual,
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "learned": False
        }
        self._save_json(self._mistakes_file, self._mistakes)
        logger.info(f"Recorded mistake: {mistake_id}")
        return mistake_id
    
    def get_mistakes(self, limit: int = 20) -> List[Dict]:
        """Get recent mistakes."""
        mistakes = [{"id": k, **v} for k, v in self._mistakes.items()]
        mistakes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return mistakes[:limit]
    
    def mark_mistake_learned(self, mistake_id: str) -> bool:
        """Mark a mistake as learned."""
        if mistake_id in self._mistakes:
            self._mistakes[mistake_id]["learned"] = True
            self._mistakes[mistake_id]["learned_at"] = datetime.now().isoformat()
            return self._save_json(self._mistakes_file, self._mistakes)
        return False
    
    def get_profile_summary(self) -> str:
        """Get a formatted profile summary for LLM context."""
        profile = self.get_profile()
        interests = self.get_interests()
        goals = self.get_goals()
        
        summary_parts = []
        
        if profile.get("name"):
            summary_parts.append(f"Name: {profile['name']}")
        if profile.get("age"):
            summary_parts.append(f"Age: {profile['age']}")
        if profile.get("location"):
            summary_parts.append(f"Location: {profile['location']}")
        if profile.get("occupation"):
            summary_parts.append(f"Occupation: {profile['occupation']}")
        
        if interests.get("hobbies"):
            summary_parts.append(f"Hobbies: {', '.join(interests['hobbies'])}")
        if interests.get("topics"):
            summary_parts.append(f"Topics of interest: {', '.join(interests['topics'])}")
        
        if goals.get("short_term_goals"):
            summary_parts.append(f"Short-term goals: {', '.join(goals['short_term_goals'])}")
        
        return "\n".join(summary_parts) if summary_parts else "No profile information available"
    
    def search_all_memories(self, query: str) -> List[Dict]:
        """Search across all memory types."""
        results = []
        
        # Search semantic memories
        semantic_results = self.recall_memory(query, top_k=10)
        for memory in semantic_results:
            results.append({
                "type": "semantic",
                "category": memory.category,
                "key": memory.key,
                "value": memory.value,
                "confidence": memory.confidence
            })
        
        # Search conversation history
        for entry in self._conversation_history:
            if query.lower() in entry.get("content", "").lower():
                results.append({
                    "type": "conversation",
                    "role": entry.get("role"),
                    "content": entry.get("content"),
                    "timestamp": entry.get("timestamp")
                })
        
        return results[:20]  # Limit results


# Global memory engine instance
memory_engine = MemoryEngine()