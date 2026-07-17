"""Semantic Memory Graph for JARVIS NLP.

Connect memories with relationships.
User → Programming → Python → FastAPI → Current Project → GitHub Repo
Now AI understands relationships.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# MEMORY NODE
# ════════════════════════════════════════════════════════════════════

@dataclass
class MemoryNode:
    """A node in the semantic memory graph."""
    id: str = ""
    content: str = ""
    memory_type: str = ""  # episodic, semantic, procedural, preference
    importance: float = 0.5
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = 0.0
    access_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": round(self.importance, 3),
            "metadata": self.metadata,
            "access_count": self.access_count,
        }


@dataclass
class MemoryEdge:
    """A relationship between two memories."""
    source_id: str = ""
    target_id: str = ""
    relationship: str = ""  # related_to, caused_by, follows, part_of, etc.
    weight: float = 1.0
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "relationship": self.relationship,
            "weight": round(self.weight, 3),
        }


# ════════════════════════════════════════════════════════════════════
# SEMANTIC MEMORY GRAPH
# ════════════════════════════════════════════════════════════════════

class SemanticMemoryGraph:
    """Connects memories with semantic relationships.

    Supports:
    - Adding memories as nodes
    - Creating relationships between memories
    - Traversing memory chains
    - Finding related memories
    - Memory clustering by topic
    """

    def __init__(self) -> None:
        self._nodes: dict[str, MemoryNode] = {}
        self._edges: list[MemoryEdge] = []
        self._adjacency: dict[str, list[int]] = {}
        self._next_id: int = 1
        self._topic_clusters: dict[str, list[str]] = {}

    def add_memory(
        self,
        content: str,
        memory_type: str = "episodic",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryNode:
        """Add a memory to the graph."""
        node_id = f"mem_{self._next_id}"
        self._next_id += 1

        node = MemoryNode(
            id=node_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {},
            created_at=time.time(),
            last_accessed=time.time(),
        )

        self._nodes[node_id] = node
        return node

    def connect(
        self,
        source_id: str,
        target_id: str,
        relationship: str = "related_to",
        weight: float = 1.0,
        context: str = "",
    ) -> MemoryEdge | None:
        """Create a relationship between two memories."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        edge = MemoryEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=weight,
            context=context,
        )

        self._edges.append(edge)
        edge_idx = len(self._edges) - 1

        if source_id not in self._adjacency:
            self._adjacency[source_id] = []
        self._adjacency[source_id].append(edge_idx)

        return edge

    def find_related(
        self,
        content_query: str,
        limit: int = 5,
    ) -> list[MemoryNode]:
        """Find memories related to a content query."""
        query_lower = content_query.lower()
        scored: list[tuple[float, MemoryNode]] = []

        for node in self._nodes.values():
            # Simple content similarity
            content_lower = node.content.lower()
            score = 0.0

            # Exact match
            if query_lower in content_lower:
                score = 1.0
            else:
                # Word overlap
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                if query_words and content_words:
                    overlap = len(query_words & content_words)
                    score = overlap / max(len(query_words), 1)

            if score > 0:
                # Boost by importance and recency
                score *= (0.7 + 0.3 * node.importance)
                scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored[:limit]]

    def traverse_from(
        self,
        memory_id: str,
        max_depth: int = 3,
    ) -> list[tuple[str, str, int]]:
        """Traverse from a memory node, returning connected memories.

        Returns list of (content, relationship, depth).
        """
        if memory_id not in self._nodes:
            return []

        visited: set[str] = {memory_id}
        queue: list[tuple[str, int]] = [(memory_id, 0)]
        results: list[tuple[str, str, int]] = []

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            edge_indices = self._adjacency.get(current_id, [])
            for idx in edge_indices:
                edge = self._edges[idx]
                target_id = edge.target_id
                if target_id not in visited:
                    visited.add(target_id)
                    target = self._nodes[target_id]
                    results.append((target.content, edge.relationship, depth + 1))
                    queue.append((target_id, depth + 1))

        return results

    def get_memory_chain(self, memory_id: str, max_length: int = 10) -> list[MemoryNode]:
        """Get a chain of related memories starting from a given memory."""
        if memory_id not in self._nodes:
            return []

        chain = [self._nodes[memory_id]]
        visited = {memory_id}
        current_id = memory_id

        for _ in range(max_length - 1):
            edge_indices = self._adjacency.get(current_id, [])
            if not edge_indices:
                break

            # Get the strongest connection
            best_edge = None
            best_weight = 0
            for idx in edge_indices:
                edge = self._edges[idx]
                if edge.target_id not in visited and edge.weight > best_weight:
                    best_edge = edge
                    best_weight = edge.weight

            if not best_edge:
                break

            visited.add(best_edge.target_id)
            target = self._nodes[best_edge.target_id]
            chain.append(target)
            current_id = best_edge.target_id

        return chain

    def cluster_by_topic(self) -> dict[str, list[str]]:
        """Group memories into topic clusters based on content similarity."""
        clusters: dict[str, list[str]] = {}

        for node in self._nodes.values():
            # Simple topic detection based on keywords
            content_lower = node.content.lower()
            topic = self._detect_topic(content_lower)

            if topic not in clusters:
                clusters[topic] = []
            clusters[topic].append(node.content)

        self._topic_clusters = clusters
        return clusters

    def get_stats(self) -> dict[str, Any]:
        """Return graph statistics."""
        return {
            "total_memories": len(self._nodes),
            "total_connections": len(self._edges),
            "avg_importance": (
                sum(n.importance for n in self._nodes.values()) / len(self._nodes)
                if self._nodes else 0
            ),
            "topics": list(self._topic_clusters.keys()),
        }

    @staticmethod
    def _detect_topic(content: str) -> str:
        """Simple topic detection from content."""
        topics = {
            "programming": ["code", "python", "javascript", "function", "bug", "git"],
            "entertainment": ["music", "video", "movie", "game", "play", "watch"],
            "productivity": ["task", "reminder", "note", "calendar", "meeting"],
            "system": ["volume", "brightness", "wifi", "shutdown", "screenshot"],
            "knowledge": ["learn", "research", "study", "explain", "what is"],
            "communication": ["email", "message", "call", "phone", "chat"],
        }

        for topic, keywords in topics.items():
            if any(kw in content for kw in keywords):
                return topic

        return "general"


# ════════════════════════════════════════════════════════════════════
# USER DIGITAL TWIN
# ════════════════════════════════════════════════════════════════════

@dataclass
class DigitalTwin:
    """Comprehensive user profile - the 'digital twin'."""
    # Identity
    name: str = ""
    timezone: str = ""

    # Skills & Knowledge
    programming_languages: list[str] = field(default_factory=list)
    technical_skills: list[str] = field(default_factory=list)
    study_subjects: list[str] = field(default_factory=list)

    # Projects
    current_projects: list[str] = field(default_factory=list)
    past_projects: list[str] = field(default_factory=list)
    github_repos: list[str] = field(default_factory=list)

    # Preferences
    favorite_tools: dict[str, str] = field(default_factory=dict)
    favorite_search_engines: list[str] = field(default_factory=list)
    preferred_response_style: str = "casual"
    preferred_coding_language: str = ""

    # Behavior
    daily_routine: dict[str, list[str]] = field(default_factory=dict)
    frequent_commands: list[str] = field(default_factory=list)
    session_types: dict[str, int] = field(default_factory=dict)

    # Goals & Interests
    interests: list[str] = field(default_factory=list)
    current_goals: list[str] = field(default_factory=list)
    learning_topics: list[str] = field(default_factory=list)

    # Statistics
    total_interactions: int = 0
    most_used_intents: dict[str, int] = field(default_factory=dict)
    most_used_tools: dict[str, int] = field(default_factory=dict)
    average_session_length: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "programming_languages": self.programming_languages,
            "technical_skills": self.technical_skills,
            "current_projects": self.current_projects,
            "favorite_tools": self.favorite_tools,
            "preferred_response_style": self.preferred_response_style,
            "interests": self.interests,
            "current_goals": self.current_goals,
            "total_interactions": self.total_interactions,
            "most_used_intents": self.most_used_intents,
            "most_used_tools": self.most_used_tools,
        }


class UserDigitalTwin:
    """Gradually builds a comprehensive user profile.

    Stores projects, skills, goals, interests, tools, routines.
    Never exposes this directly. Only improves personalization.
    """

    def __init__(self) -> None:
        self._twin = DigitalTwin()
        self._interaction_history: list[dict[str, Any]] = []
        self._learning_rate: float = 0.1

    def update_from_interaction(
        self,
        intent: str,
        entities: dict[str, Any],
        tool: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Update the digital twin from a user interaction."""
        self._twin.total_interactions += 1

        # Track intent usage
        self._twin.most_used_intents[intent] = (
            self._twin.most_used_intents.get(intent, 0) + 1
        )

        # Track tool usage
        if tool:
            self._twin.most_used_tools[tool] = (
                self._twin.most_used_tools.get(tool, 0) + 1
            )

        # Learn from specific intents
        intent_lower = intent.lower()

        if intent_lower in ("open_vscode", "programming", "run_code"):
            lang = entities.get("language", "")
            if lang and lang not in self._twin.programming_languages:
                self._twin.programming_languages.append(lang)

        if intent_lower in ("open_app", "open_vscode", "open_chrome"):
            app = entities.get("app", entities.get("target", ""))
            if app and app not in self._twin.favorite_tools.values():
                self._twin.favorite_tools[app] = app

        if intent_lower in ("search_web", "web_search"):
            query = entities.get("query", "")
            if query:
                # Detect interests from search queries
                self._detect_interests(query)

        # Store interaction
        self._interaction_history.append({
            "intent": intent,
            "entities": entities,
            "tool": tool,
            "timestamp": time.time(),
        })

        # Keep only recent history
        if len(self._interaction_history) > 500:
            self._interaction_history = self._interaction_history[-500:]

    def get_profile(self) -> DigitalTwin:
        """Get the current digital twin profile."""
        return self._twin

    def get_summary(self) -> str:
        """Get a human-readable summary of the user profile."""
        parts = []

        if self._twin.programming_languages:
            parts.append(f"Languages: {', '.join(self._twin.programming_languages)}")

        if self._twin.interests:
            parts.append(f"Interests: {', '.join(self._twin.interests[:5])}")

        if self._twin.favorite_tools:
            tools = list(self._twin.favorite_tools.values())[:5]
            parts.append(f"Tools: {', '.join(tools)}")

        if self._twin.current_projects:
            parts.append(f"Projects: {', '.join(self._twin.current_projects[:3])}")

        parts.append(f"Interactions: {self._twin.total_interactions}")

        return " | ".join(parts) if parts else "New user - still learning"

    def get_response_style(self) -> str:
        """Determine preferred response style based on user profile."""
        # If user is technical, be more concise
        if len(self._twin.programming_languages) > 2:
            return "technical"

        # If user asks many questions, be more explanatory
        question_count = sum(
            1 for i in self._interaction_history[-50:]
            if i["intent"] in ("DEFINITION", "EXPLAIN", "HOW_TO")
        )
        if question_count > 10:
            return "explanatory"

        return self._twin.preferred_response_style

    def _detect_interests(self, query: str) -> None:
        """Detect user interests from search queries."""
        interest_keywords = {
            "ai": "Artificial Intelligence",
            "machine learning": "Machine Learning",
            "python": "Python Programming",
            "javascript": "JavaScript Programming",
            "web": "Web Development",
            "design": "Design",
            "music": "Music",
            "movie": "Movies",
            "game": "Gaming",
            "stock": "Finance",
            "crypto": "Cryptocurrency",
            "fitness": "Fitness",
            "cook": "Cooking",
        }

        query_lower = query.lower()
        for keyword, interest in interest_keywords.items():
            if keyword in query_lower:
                if interest not in self._twin.interests:
                    self._twin.interests.append(interest)
                    # Keep only top 10 interests
                    if len(self._twin.interests) > 10:
                        self._twin.interests = self._twin.interests[-10:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_interactions": self._twin.total_interactions,
            "programming_languages": len(self._twin.programming_languages),
            "interests": len(self._twin.interests),
            "favorite_tools": len(self._twin.favorite_tools),
        }


# ════════════════════════════════════════════════════════════════════
# TOOL HEALTH SYSTEM
# ════════════════════════════════════════════════════════════════════

@dataclass
class ToolHealth:
    """Health status for a tool/API."""
    tool_name: str = ""
    api_status: str = "unknown"  # healthy, degraded, unhealthy, unknown
    latency_ms: float = 0.0
    failure_rate: float = 0.0
    success_rate: float = 1.0
    rate_limit_remaining: int = -1
    rate_limit_total: int = -1
    auth_valid: bool = True
    last_check: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    is_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "api_status": self.api_status,
            "latency_ms": round(self.latency_ms, 1),
            "failure_rate": round(self.failure_rate, 3),
            "success_rate": round(self.success_rate, 3),
            "is_available": self.is_available,
            "consecutive_failures": self.consecutive_failures,
        }


class ToolHealthSystem:
    """Monitors tool health continuously.

    Tracks API status, latency, failure rate, success rate,
    rate limits, authentication, availability.
    Automatically disables unhealthy providers.
    """

    def __init__(self) -> None:
        self._health: dict[str, ToolHealth] = {}
        self._check_interval: float = 300.0  # 5 minutes
        self._failure_threshold: int = 5  # Consecutive failures before marking unhealthy
        self._latency_threshold: float = 5000.0  # 5 seconds

    def record_execution(
        self,
        tool_name: str,
        success: bool,
        latency_ms: float = 0.0,
        error: str = "",
    ) -> ToolHealth:
        """Record a tool execution for health tracking."""
        if tool_name not in self._health:
            self._health[tool_name] = ToolHealth(tool_name=tool_name)

        health = self._health[tool_name]
        health.last_check = time.time()

        if success:
            health.success_rate = min(1.0, health.success_rate + 0.05)
            health.consecutive_failures = 0
            health.api_status = "healthy"
            health.is_available = True
        else:
            health.failure_rate = min(1.0, health.failure_rate + 0.1)
            health.consecutive_failures += 1
            health.last_failure = time.time()

            if health.consecutive_failures >= self._failure_threshold:
                health.api_status = "unhealthy"
                health.is_available = False
            elif health.consecutive_failures >= 2:
                health.api_status = "degraded"

        if latency_ms > 0:
            # Exponential moving average
            health.latency_ms = 0.7 * health.latency_ms + 0.3 * latency_ms
            if health.latency_ms > self._latency_threshold:
                health.api_status = "degraded"

        return health

    def get_health(self, tool_name: str) -> ToolHealth:
        """Get health status for a tool."""
        if tool_name not in self._health:
            return ToolHealth(tool_name=tool_name)
        return self._health[tool_name]

    def is_healthy(self, tool_name: str) -> bool:
        """Check if a tool is healthy."""
        health = self.get_health(tool_name)
        return health.is_available and health.api_status != "unhealthy"

    def get_best_tool(self, candidates: list[str]) -> str | None:
        """Select the best tool from candidates based on health."""
        if not candidates:
            return None

        scored: list[tuple[float, str]] = []
        for name in candidates:
            health = self.get_health(name)
            if not health.is_available:
                continue

            # Score: success rate (40%) + low latency (30%) + low failure rate (30%)
            latency_score = 1.0 / (1.0 + health.latency_ms / 1000.0)
            score = (
                0.40 * health.success_rate
                + 0.30 * latency_score
                + 0.30 * (1.0 - health.failure_rate)
            )
            scored.append((score, name))

        if not scored:
            return candidates[0]  # Fallback to first candidate

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def get_all_health(self) -> dict[str, ToolHealth]:
        """Get health status for all tools."""
        return dict(self._health)

    def get_stats(self) -> dict[str, Any]:
        """Return health system statistics."""
        tools = list(self._health.values())
        return {
            "total_tools_monitored": len(tools),
            "healthy": sum(1 for t in tools if t.api_status == "healthy"),
            "degraded": sum(1 for t in tools if t.api_status == "degraded"),
            "unhealthy": sum(1 for t in tools if t.api_status == "unhealthy"),
            "avg_latency": sum(t.latency_ms for t in tools) / len(tools) if tools else 0,
        }


# ════════════════════════════════════════════════════════════════════
# ERROR EXPLANATION
# ════════════════════════════════════════════════════════════════════

class ErrorExplainer:
    """Explains errors with Cause → Impact → Solution → Prevention.

    Instead of "Error occurred.", explain:
    - What caused the error
    - What impact it has
    - How to fix it
    - How to prevent it in the future
    """

    ERROR_DATABASE: dict[str, dict[str, str]] = {
        "file_not_found": {
            "cause": "The file you're looking for doesn't exist at the specified path.",
            "impact": "Cannot read or process the file.",
            "solution": "Check the file path and name. Make sure the file exists.",
            "prevention": "Use file search to find the correct path before accessing.",
        },
        "permission_denied": {
            "cause": "You don't have sufficient permissions to access this resource.",
            "impact": "Cannot read, write, or execute the requested operation.",
            "solution": "Run with elevated permissions or ask an administrator.",
            "prevention": "Check file permissions before attempting access.",
        },
        "network_error": {
            "cause": "Unable to connect to the network or the requested server.",
            "impact": "Cannot fetch data or communicate with external services.",
            "solution": "Check your internet connection and try again.",
            "prevention": "Verify network connectivity before making requests.",
        },
        "timeout": {
            "cause": "The operation took too long to complete.",
            "impact": "The request was aborted before completion.",
            "solution": "Try again later or break the task into smaller parts.",
            "prevention": "Set appropriate timeouts and use async operations.",
        },
        "rate_limit": {
            "cause": "Too many requests were sent to the API.",
            "impact": "Additional requests are temporarily blocked.",
            "solution": "Wait a moment and try again.",
            "prevention": "Implement request throttling and caching.",
        },
        "auth_failed": {
            "cause": "Authentication credentials are invalid or expired.",
            "impact": "Cannot access protected resources.",
            "solution": "Refresh your authentication token or re-login.",
            "prevention": "Implement token refresh and handle auth expiry gracefully.",
        },
        "memory_error": {
            "cause": "Insufficient memory to complete the operation.",
            "impact": "Operation failed or was terminated.",
            "solution": "Close other applications or increase available memory.",
            "prevention": "Monitor memory usage and implement memory-efficient algorithms.",
        },
    }

    def explain(self, error_type: str, details: str = "") -> dict[str, str]:
        """Generate a structured error explanation.

        Returns dict with cause, impact, solution, prevention.
        """
        template = self.ERROR_DATABASE.get(error_type, {
            "cause": f"An error occurred: {error_type}",
            "impact": "The requested operation could not be completed.",
            "solution": "Please try again or contact support.",
            "prevention": "Ensure all prerequisites are met before retrying.",
        })

        if details:
            template["cause"] += f" Details: {details}"

        return template

    def explain_to_user(self, error_type: str, details: str = "") -> str:
        """Generate a user-friendly error explanation."""
        explanation = self.explain(error_type, details)
        return (
            f"Cause: {explanation['cause']}\n"
            f"Impact: {explanation['impact']}\n"
            f"Solution: {explanation['solution']}\n"
            f"Prevention: {explanation['prevention']}"
        )


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCES
# ════════════════════════════════════════════════════════════════════

semantic_memory_graph = SemanticMemoryGraph()
user_digital_twin = UserDigitalTwin()
tool_health_system = ToolHealthSystem()
error_explainer = ErrorExplainer()
