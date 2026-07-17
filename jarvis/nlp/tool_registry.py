"""Dynamic Tool Discovery & Auto-Registration for JARVIS NLP.

Every installed tool automatically registers itself.
The NLP never needs manual updates.

New Tool Added → Registry Updated → Capabilities Indexed → Immediately Available.
No hardcoding.
"""

from __future__ import annotations

import os
import time
import importlib
import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# TOOL METADATA
# ════════════════════════════════════════════════════════════════════

@dataclass
class ToolCapability:
    """A single capability a tool provides."""
    name: str
    description: str = ""
    input_types: list[str] = field(default_factory=list)
    output_types: list[str] = field(default_factory=list)
    estimated_time_ms: float = 100.0
    requires_network: bool = False
    requires_elevated: bool = False


@dataclass
class ToolMetadata:
    """Complete metadata for a registered tool."""
    name: str
    module_path: str
    handler: str = ""
    purpose: str = ""
    capabilities: list[ToolCapability] = field(default_factory=list)
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    estimated_time_ms: float = 100.0
    success_rate: float = 1.0
    total_calls: int = 0
    total_failures: int = 0
    avg_latency_ms: float = 0.0
    last_used: float = 0.0
    registered_at: float = field(default_factory=time.time)
    priority: int = 50  # 0=highest, 100=lowest
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "module_path": self.module_path,
            "handler": self.handler,
            "purpose": self.purpose,
            "capabilities": [c.name for c in self.capabilities],
            "success_rate": round(self.success_rate, 3),
            "total_calls": self.total_calls,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "estimated_time_ms": self.estimated_time_ms,
            "priority": self.priority,
            "tags": self.tags,
        }


# ════════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ════════════════════════════════════════════════════════════════════

class DynamicToolRegistry:
    """Auto-discovering tool registry that indexes capabilities.

    Tools register themselves and their capabilities automatically.
    The NLP selects tools based on capabilities, not keywords.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolMetadata] = {}
        self._capability_index: dict[str, list[str]] = {}
        self._tag_index: dict[str, list[str]] = {}
        self._scan_paths: list[str] = []
        self._auto_scan_enabled: bool = True
        self._last_scan_time: float = 0.0

    # ── Registration ──────────────────────────────────────────────

    def register(
        self,
        name: str,
        module_path: str,
        handler: str = "",
        purpose: str = "",
        capabilities: list[dict[str, Any]] | None = None,
        limitations: list[str] | None = None,
        dependencies: list[str] | None = None,
        estimated_time_ms: float = 100.0,
        tags: list[str] | None = None,
    ) -> ToolMetadata:
        """Register a tool with its capabilities.

        Args:
            name: Unique tool identifier.
            module_path: Dotted module path (e.g., 'jarvis.tools.youtube').
            handler: Handler function name within the module.
            purpose: Human-readable purpose description.
            capabilities: List of capability dicts with name, description, etc.
            limitations: Known limitations of the tool.
            dependencies: External dependencies required.
            estimated_time_ms: Average execution time estimate.
            tags: Searchable tags for categorization.

        Returns:
            The registered ToolMetadata.
        """
        caps = [
            ToolCapability(
                name=c.get("name", ""),
                description=c.get("description", ""),
                input_types=c.get("input_types", []),
                output_types=c.get("output_types", []),
                estimated_time_ms=c.get("estimated_time_ms", estimated_time_ms),
                requires_network=c.get("requires_network", False),
                requires_elevated=c.get("requires_elevated", False),
            )
            for c in (capabilities or [])
        ]

        meta = ToolMetadata(
            name=name,
            module_path=module_path,
            handler=handler,
            purpose=purpose,
            capabilities=caps,
            limitations=limitations or [],
            dependencies=dependencies or [],
            estimated_time_ms=estimated_time_ms,
            tags=tags or [],
        )

        self._tools[name] = meta
        self._index_tool(meta)

        logger.info("Tool registered: %s (%s)", name, module_path)
        return meta

    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry."""
        if name not in self._tools:
            return False
        meta = self._tools.pop(name)
        self._unindex_tool(meta)
        logger.info("Tool unregistered: %s", name)
        return True

    # ── Discovery ─────────────────────────────────────────────────

    def scan_directory(self, directory: str, pattern: str = "*.py") -> int:
        """Scan a directory for tool modules and auto-register them.

        Returns the number of new tools registered.
        """
        import glob as glob_mod

        registered = 0
        search_pattern = os.path.join(directory, "**", pattern)

        for filepath in glob_mod.glob(search_pattern, recursive=True):
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            if module_name.startswith("_"):
                continue

            # Try to import and register
            try:
                rel_path = os.path.relpath(filepath, os.path.dirname(directory))
                module_path = rel_path.replace(os.sep, ".").replace(".py", "")

                if module_path in [t.module_path for t in self._tools.values()]:
                    continue

                mod = importlib.import_module(module_path)
                if hasattr(mod, "TOOL_META"):
                    meta = mod.TOOL_META
                    if isinstance(meta, dict):
                        self.register(**meta)
                        registered += 1
                elif hasattr(mod, "register_tool"):
                    mod.register_tool(self)
                    registered += 1

            except Exception as e:
                logger.debug("Skip %s: %s", filepath, e)

        self._last_scan_time = time.time()
        return registered

    def auto_discover(self) -> int:
        """Auto-discover tools from configured scan paths.

        Returns total number of registered tools.
        """
        if not self._auto_scan_enabled:
            return len(self._tools)

        for scan_path in self._scan_paths:
            if os.path.isdir(scan_path):
                self.scan_directory(scan_path)

        return len(self._tools)

    def add_scan_path(self, path: str) -> None:
        """Add a directory to scan for tools."""
        if path not in self._scan_paths:
            self._scan_paths.append(path)

    # ── Capability-based lookup ───────────────────────────────────

    def find_by_capability(self, capability: str) -> list[ToolMetadata]:
        """Find all tools that provide a specific capability.

        Returns tools sorted by success rate and priority.
        """
        tool_names = self._capability_index.get(capability, [])
        tools = [self._tools[n] for n in tool_names if n in self._tools]
        return sorted(tools, key=lambda t: (-t.success_rate, t.priority))

    def find_by_tag(self, tag: str) -> list[ToolMetadata]:
        """Find all tools with a specific tag."""
        tool_names = self._tag_index.get(tag, [])
        return [self._tools[n] for n in tool_names if n in self._tools]

    def find_best_for_task(
        self,
        required_capabilities: list[str],
        context: dict[str, Any] | None = None,
    ) -> ToolMetadata | None:
        """Find the best tool for a task requiring specific capabilities.

        Ranks by:
        1. Capability coverage (how many required caps it has)
        2. Success rate
        3. Priority
        4. Latency
        5. User preference (from context)
        """
        candidates: list[tuple[float, ToolMetadata]] = []

        for name, meta in self._tools.items():
            tool_caps = {c.name for c in meta.capabilities}
            required_set = set(required_capabilities)

            coverage = len(tool_caps & required_set) / len(required_set) if required_set else 0
            if coverage == 0:
                continue

            # Score: capability coverage (40%) + success rate (30%) + priority (20%) + latency (10%)
            priority_score = 1.0 - (meta.priority / 100.0)
            latency_score = 1.0 / (1.0 + meta.avg_latency_ms / 1000.0)

            score = (
                0.40 * coverage
                + 0.30 * meta.success_rate
                + 0.20 * priority_score
                + 0.10 * latency_score
            )

            candidates.append((score, meta))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    # ── Performance tracking ──────────────────────────────────────

    def record_execution(
        self,
        tool_name: str,
        success: bool,
        latency_ms: float = 0.0,
    ) -> None:
        """Record a tool execution for performance tracking."""
        meta = self._tools.get(tool_name)
        if not meta:
            return

        meta.total_calls += 1
        meta.last_used = time.time()

        if not success:
            meta.total_failures += 1

        # Update success rate (exponential moving average)
        alpha = 0.1
        meta.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * meta.success_rate

        # Update average latency
        if latency_ms > 0:
            n = meta.total_calls
            meta.avg_latency_ms = ((n - 1) * meta.avg_latency_ms + latency_ms) / n

    def get_tool(self, name: str) -> ToolMetadata | None:
        """Get metadata for a specific tool."""
        return self._tools.get(name)

    def get_all_tools(self) -> list[ToolMetadata]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_stats(self) -> dict[str, Any]:
        """Return registry statistics."""
        tools = list(self._tools.values())
        return {
            "total_tools": len(tools),
            "total_capabilities": len(self._capability_index),
            "avg_success_rate": (
                sum(t.success_rate for t in tools) / len(tools) if tools else 0
            ),
            "total_executions": sum(t.total_calls for t in tools),
            "last_scan_time": self._last_scan_time,
        }

    # ── Internal helpers ───────────────────────────────────────────

    def _index_tool(self, meta: ToolMetadata) -> None:
        """Add a tool's capabilities and tags to the search indices."""
        for cap in meta.capabilities:
            if cap.name not in self._capability_index:
                self._capability_index[cap.name] = []
            if meta.name not in self._capability_index[cap.name]:
                self._capability_index[cap.name].append(meta.name)

        for tag in meta.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if meta.name not in self._tag_index[tag]:
                self._tag_index[tag].append(meta.name)

    def _unindex_tool(self, meta: ToolMetadata) -> None:
        """Remove a tool from the search indices."""
        for cap in meta.capabilities:
            if cap.name in self._capability_index:
                self._capability_index[cap.name] = [
                    n for n in self._capability_index[cap.name] if n != meta.name
                ]
        for tag in meta.tags:
            if tag in self._tag_index:
                self._tag_index[tag] = [
                    n for n in self._tag_index[tag] if n != meta.name
                ]


# ════════════════════════════════════════════════════════════════════
# BUILT-IN TOOL REGISTRATIONS
# ════════════════════════════════════════════════════════════════════

def register_builtins(registry: DynamicToolRegistry) -> None:
    """Register all built-in JARVIS tools."""

    # YouTube
    registry.register(
        name="youtube",
        module_path="jarvis.tools.youtube",
        handler="play",
        purpose="Search, play, and manage YouTube videos",
        capabilities=[
            {"name": "video_search", "description": "Search YouTube videos", "requires_network": True},
            {"name": "video_play", "description": "Play a YouTube video"},
            {"name": "video_pause", "description": "Pause video playback"},
            {"name": "video_resume", "description": "Resume video playback"},
            {"name": "playlist_management", "description": "Manage playlists"},
            {"name": "channel_info", "description": "Get channel information", "requires_network": True},
            {"name": "video_transcript", "description": "Extract video transcript", "requires_network": True},
            {"name": "url_open", "description": "Open a YouTube URL directly"},
        ],
        estimated_time_ms=2000,
        tags=["entertainment", "video", "music", "streaming"],
    )

    # Spotify
    registry.register(
        name="spotify",
        module_path="jarvis.tools.spotify",
        handler="play",
        purpose="Play music via Spotify",
        capabilities=[
            {"name": "music_search", "description": "Search Spotify tracks", "requires_network": True},
            {"name": "music_play", "description": "Play a track or playlist"},
            {"name": "music_pause", "description": "Pause playback"},
            {"name": "music_resume", "description": "Resume playback"},
            {"name": "playlist_management", "description": "Manage playlists"},
            {"name": "artist_info", "description": "Get artist information"},
        ],
        estimated_time_ms=1500,
        tags=["entertainment", "music", "streaming"],
    )

    # Web Search
    registry.register(
        name="web_search",
        module_path="jarvis.tools.web_search",
        handler="search",
        purpose="Search the web for information",
        capabilities=[
            {"name": "web_search", "description": "General web search", "requires_network": True},
            {"name": "image_search", "description": "Search for images", "requires_network": True},
            {"name": "news_search", "description": "Search for news", "requires_network": True},
        ],
        estimated_time_ms=1000,
        tags=["knowledge", "search", "information"],
    )

    # GitHub
    registry.register(
        name="github",
        module_path="jarvis.tools.github",
        handler="search",
        purpose="Search and interact with GitHub repositories",
        capabilities=[
            {"name": "repo_search", "description": "Search GitHub repositories", "requires_network": True},
            {"name": "repo_info", "description": "Get repository information", "requires_network": True},
            {"name": "readme_read", "description": "Read repository README", "requires_network": True},
            {"name": "issue_tracking", "description": "Track issues", "requires_network": True},
        ],
        estimated_time_ms=1500,
        tags=["programming", "development", "code"],
    )

    # Open App
    registry.register(
        name="open_app",
        module_path="jarvis.tools.open_app",
        handler="open",
        purpose="Launch desktop applications",
        capabilities=[
            {"name": "app_launch", "description": "Launch an application"},
            {"name": "app_search", "description": "Search for installed apps"},
        ],
        estimated_time_ms=500,
        tags=["system", "productivity"],
    )

    # System Control
    registry.register(
        name="system_control",
        module_path="jarvis.system_control",
        handler="control",
        purpose="Control system settings (volume, brightness, etc.)",
        capabilities=[
            {"name": "volume_control", "description": "Adjust system volume"},
            {"name": "brightness_control", "description": "Adjust screen brightness"},
            {"name": "wifi_control", "description": "Toggle WiFi"},
            {"name": "bluetooth_control", "description": "Toggle Bluetooth"},
            {"name": "screenshot", "description": "Take a screenshot"},
            {"name": "system_power", "description": "Shutdown/restart/sleep"},
            {"name": "lock_screen", "description": "Lock the screen"},
        ],
        estimated_time_ms=300,
        tags=["system", "control"],
    )

    # File Management
    registry.register(
        name="file_management",
        module_path="jarvis.tools.file_management",
        handler="manage",
        purpose="Manage files and folders",
        capabilities=[
            {"name": "file_search", "description": "Search for files"},
            {"name": "file_read", "description": "Read file contents"},
            {"name": "file_write", "description": "Write to files"},
            {"name": "file_copy", "description": "Copy files"},
            {"name": "file_move", "description": "Move files"},
            {"name": "file_delete", "description": "Delete files"},
            {"name": "folder_create", "description": "Create folders"},
            {"name": "folder_list", "description": "List folder contents"},
        ],
        estimated_time_ms=200,
        tags=["system", "productivity", "files"],
    )

    # Memory
    registry.register(
        name="memory",
        module_path="jarvis.memory",
        handler="store",
        purpose="Store and recall information from memory",
        capabilities=[
            {"name": "memory_store", "description": "Store information"},
            {"name": "memory_recall", "description": "Recall stored information"},
            {"name": "memory_search", "description": "Search memory entries"},
            {"name": "memory_delete", "description": "Delete memory entries"},
        ],
        estimated_time_ms=100,
        tags=["memory", "productivity"],
    )

    # Calculator
    registry.register(
        name="calculator",
        module_path="jarvis.tools.calculator",
        handler="calculate",
        purpose="Perform calculations and unit conversions",
        capabilities=[
            {"name": "math_calculate", "description": "Perform math calculations"},
            {"name": "unit_convert", "description": "Convert between units"},
            {"name": "currency_convert", "description": "Convert currencies", "requires_network": True},
        ],
        estimated_time_ms=50,
        tags=["productivity", "math"],
    )

    # Programming
    registry.register(
        name="programming",
        module_path="jarvis.tools.programming",
        handler="assist",
        purpose="Programming assistance and code analysis",
        capabilities=[
            {"name": "code_analysis", "description": "Analyze code"},
            {"name": "code_review", "description": "Review code quality"},
            {"name": "error_explanation", "description": "Explain errors"},
            {"name": "code_suggestion", "description": "Suggest code improvements"},
            {"name": "refactoring", "description": "Suggest refactoring"},
        ],
        estimated_time_ms=500,
        tags=["programming", "development"],
    )


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

tool_registry = DynamicToolRegistry()

# Register built-in tools on import
register_builtins(tool_registry)
