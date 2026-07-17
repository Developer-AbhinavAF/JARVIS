"""Capability detection for the JARVIS NLP engine.

Maps intents and entities to system capabilities, checks availability,
and resolves default handler module paths.
"""

from __future__ import annotations

import importlib
import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.nlp.utils import GoalCategory


# ════════════════════════════════════════════════════════════════════
# CAPABILITY MAP
# ════════════════════════════════════════════════════════════════════

CAPABILITY_MAP: dict[str, dict[str, object]] = {
    "browser": {
        "description": "Web browser control",
        "requirements": ["web_browser", "internet"],
        "handler": "jarvis.tools.browser",
    },
    "app_launcher": {
        "description": "OS application launching",
        "requirements": ["os_app_launching"],
        "handler": "jarvis.tools.open_app",
    },
    "search_engine": {
        "description": "Internet search",
        "requirements": ["internet_search", "internet"],
        "handler": "jarvis.tools.search",
    },
    "media_player": {
        "description": "Media playback control",
        "requirements": ["media_playback"],
        "handler": "jarvis.tools.media",
    },
    "system_control": {
        "description": "OS system settings and control",
        "requirements": ["os_system_access"],
        "handler": "jarvis.tools.system",
    },
    "file_system": {
        "description": "File system read/write operations",
        "requirements": ["file_system_access"],
        "handler": "jarvis.tools.files",
    },
    "memory": {
        "description": "Memory and database operations",
        "requirements": ["memory_database"],
        "handler": "jarvis.tools.memory",
    },
    "calculator": {
        "description": "Computation and calculations",
        "requirements": ["computation"],
        "handler": "jarvis.tools.calculator",
    },
    "network": {
        "description": "Network and internet connectivity",
        "requirements": ["internet_connection"],
        "handler": "jarvis.tools.network",
    },
    "display": {
        "description": "Screen and display access",
        "requirements": ["screen_access"],
        "handler": "jarvis.tools.display",
    },
    "programming": {
        "description": "Code editing and development",
        "requirements": ["code_editor", "file_system_access"],
        "handler": "jarvis.tools.open_app",
    },
    "version_control": {
        "description": "Git and version control operations",
        "requirements": ["git_installed", "file_system_access"],
        "handler": "jarvis.tools.terminal",
    },
    "database": {
        "description": "Database operations",
        "requirements": ["database_access"],
        "handler": "jarvis.tools.database",
    },
    "cloud": {
        "description": "Cloud service integration",
        "requirements": ["internet_connection", "cloud_api"],
        "handler": "jarvis.tools.cloud",
    },
    "ai_ml": {
        "description": "AI and machine learning tools",
        "requirements": ["python", "ml_libraries"],
        "handler": "jarvis.tools.ai",
    },
    "security": {
        "description": "Security scanning and protection",
        "requirements": ["security_tools"],
        "handler": "jarvis.tools.security",
    },
    "automation": {
        "description": "Task automation and scripting",
        "requirements": ["scripting_engine"],
        "handler": "jarvis.tools.automation",
    },
    "data_analysis": {
        "description": "Data analysis and visualization",
        "requirements": ["python", "data_libraries"],
        "handler": "jarvis.tools.analysis",
    },
    "design": {
        "description": "Graphic design and UI tools",
        "requirements": ["design_software"],
        "handler": "jarvis.tools.design",
    },
    "video_editing": {
        "description": "Video editing and production",
        "requirements": ["video_editor"],
        "handler": "jarvis.tools.video",
    },
    "audio_editing": {
        "description": "Audio editing and production",
        "requirements": ["audio_editor"],
        "handler": "jarvis.tools.audio",
    },
    "image_editing": {
        "description": "Image editing and manipulation",
        "requirements": ["image_editor"],
        "handler": "jarvis.tools.image",
    },
    "3d_modeling": {
        "description": "3D modeling and rendering",
        "requirements": ["3d_software"],
        "handler": "jarvis.tools.3d",
    },
    "gaming": {
        "description": "Gaming and entertainment",
        "requirements": ["game_launcher"],
        "handler": "jarvis.tools.gaming",
    },
    "devops": {
        "description": "DevOps and deployment tools",
        "requirements": ["docker", "ci_cd"],
        "handler": "jarvis.tools.devops",
    },
    "testing": {
        "description": "Testing and quality assurance",
        "requirements": ["test_frameworks"],
        "handler": "jarvis.tools.testing",
    },
    "documentation": {
        "description": "Documentation and wiki tools",
        "requirements": ["markdown_editor"],
        "handler": "jarvis.tools.docs",
    },
    "collaboration": {
        "description": "Team collaboration tools",
        "requirements": ["internet_connection"],
        "handler": "jarvis.tools.collaboration",
    },
    "analytics": {
        "description": "Analytics and reporting",
        "requirements": ["analytics_tools"],
        "handler": "jarvis.tools.analytics",
    },
}

# Intent → capabilities mapping
_INTENT_CAPABILITIES: dict[str, list[str]] = {
    "OPEN_WEBSITE": ["browser"],
    "OPEN_APP": ["app_launcher"],
    "SEARCH_WEB": ["search_engine", "network"],
    "PLAY_MEDIA": ["media_player"],
    "PAUSE_MEDIA": ["media_player"],
    "STOP_MEDIA": ["media_player"],
    "NEXT_TRACK": ["media_player"],
    "PREVIOUS_TRACK": ["media_player"],
    "VOLUME_UP": ["system_control"],
    "VOLUME_DOWN": ["system_control"],
    "MUTE": ["system_control"],
    "UNMUTE": ["system_control"],
    "BRIGHTNESS_UP": ["system_control", "display"],
    "BRIGHTNESS_DOWN": ["system_control", "display"],
    "SHUTDOWN": ["system_control"],
    "RESTART": ["system_control"],
    "SLEEP": ["system_control"],
    "LOCK_SCREEN": ["system_control"],
    "CHANGE_WALLPAPER": ["system_control", "display"],
    "TAKE_SCREENSHOT": ["display"],
    "READ_FILE": ["file_system"],
    "WRITE_FILE": ["file_system"],
    "CREATE_FILE": ["file_system"],
    "DELETE_FILE": ["file_system"],
    "CREATE_FOLDER": ["file_system"],
    "OPEN_FOLDER": ["file_system"],
    "LIST_FILES": ["file_system"],
    "COPY_FILE": ["file_system"],
    "MOVE_FILE": ["file_system"],
    "SAVE_MEMORY": ["memory"],
    "RECALL_MEMORY": ["memory"],
    "DELETE_MEMORY": ["memory"],
    "CALCULATE": ["calculator"],
    "CONVERT_UNIT": ["calculator"],
    "GET_WEATHER": ["search_engine", "network"],
    "GET_NEWS": ["search_engine", "network"],
    "SET_REMINDER": ["memory"],
    "SET_TIMER": ["system_control"],
    "SEND_EMAIL": ["network"],
    "MAKE_CALL": ["system_control", "network"],
    "SEND_MESSAGE": ["network"],
    "PLAY_GAME": ["gaming"],
    "OPEN_CAMERA": ["app_launcher", "display"],
    "TAKE_PHOTO": ["app_launcher", "display"],
    "CHECK_STATUS": ["system_control", "memory"],
    "UPDATE_SYSTEM": ["system_control", "network"],
    "INSTALL_APP": ["app_launcher", "network"],
    "UNINSTALL_APP": ["app_launcher"],
    "DEFINITION": ["search_engine", "network"],
    "TRANSLATE": ["calculator"],
    "SUMMARIZE": ["memory"],
    "COMPARE": ["calculator", "memory"],
    "PROGRAMMING": ["programming", "file_system"],
    "OPEN_VSCODE": ["programming", "app_launcher"],
    "OPEN_TERMINAL": ["programming", "app_launcher"],
    "VERSION_CONTROL": ["version_control", "programming"],
    "GIT_INIT": ["version_control", "file_system"],
    "GIT_CLONE": ["version_control", "network"],
    "GIT_COMMIT": ["version_control", "file_system"],
    "GIT_PUSH": ["version_control", "network"],
    "GIT_PULL": ["version_control", "network"],
    "RUN_CODE": ["programming", "system_control"],
    "DEBUG_CODE": ["programming", "system_control"],
    "CREATE_PROJECT": ["programming", "file_system"],
    "DATABASE_QUERY": ["database"],
    "DATABASE_CONNECT": ["database", "network"],
    "CLOUD_UPLOAD": ["cloud", "network"],
    "CLOUD_DOWNLOAD": ["cloud", "network"],
    "TRAIN_MODEL": ["ai_ml", "programming"],
    "PREDICT": ["ai_ml"],
    "SECURITY_SCAN": ["security", "system_control"],
    "AUTOMATE_TASK": ["automation"],
    "ANALYZE_DATA": ["data_analysis"],
    "CREATE_DESIGN": ["design"],
    "EDIT_VIDEO": ["video_editing"],
    "EDIT_AUDIO": ["audio_editing"],
    "EDIT_IMAGE": ["image_editing"],
    "CREATE_3D_MODEL": ["3d_modeling"],
    "DEPLOY_APP": ["devops", "cloud"],
    "RUN_TESTS": ["testing", "programming"],
    "GENERATE_DOCS": ["documentation"],
    "COLLABORATE": ["collaboration", "network"],
    "VIEW_ANALYTICS": ["analytics", "network"],
}

# Entity type → additional capabilities
_ENTITY_CAPABILITIES: dict[str, list[str]] = {
    "url": ["browser"],
    "website": ["browser"],
    "app_name": ["app_launcher"],
    "file_path": ["file_system"],
    "directory": ["file_system"],
    "query": ["search_engine", "network"],
    "search_term": ["search_engine", "network"],
    "media_title": ["media_player"],
    "media_artist": ["media_player"],
    "number": ["calculator"],
    "expression": ["calculator"],
    "unit": ["calculator"],
    "email_address": ["network"],
    "phone_number": ["network"],
    "programming_language": ["programming"],
    "code_snippet": ["programming"],
    "repository": ["version_control", "programming"],
    "branch": ["version_control"],
    "commit_message": ["version_control"],
    "database_query": ["database"],
    "table_name": ["database"],
    "model_name": ["ai_ml"],
    "dataset": ["data_analysis"],
    "design_file": ["design"],
    "video_file": ["video_editing"],
    "audio_file": ["audio_editing"],
    "image_file": ["image_editing"],
    "3d_file": ["3d_modeling"],
    "deployment_target": ["devops"],
    "test_file": ["testing"],
    "documentation_file": ["documentation"],
}

# Goal category → default capabilities
_GOAL_CAPABILITIES: dict[GoalCategory, list[str]] = {}


# ════════════════════════════════════════════════════════════════════
# CAPABILITY DETECTOR
# ════════════════════════════════════════════════════════════════════


class CapabilityDetector:
    """Detects system capabilities required for an NLP request.

    Maps intents and entities to the capabilities they need,
    checks which capabilities are available on the current system,
    and resolves default handler module paths.
    """

    def detect(
        self,
        intent: str,
        entities: dict[str, object],
        goal: GoalCategory,
    ) -> list[str]:
        """Detect all capabilities needed to fulfill a request.

        Args:
            intent: Classified intent string (e.g. ``"OPEN_WEBSITE"``).
            entities: Extracted entity dict (e.g. ``{"url": "..."}``).
            goal: Goal category from the NLP pipeline.

        Returns:
            De-duplicated list of capability strings.
        """
        caps: set[str] = set()

        # 1. Intent-based capabilities
        if intent in _INTENT_CAPABILITIES:
            caps.update(_INTENT_CAPABILITIES[intent])

        # 2. Entity-based capabilities
        for entity_type in entities:
            if entity_type in _ENTITY_CAPABILITIES:
                caps.update(_ENTITY_CAPABILITIES[entity_type])

        # 3. Goal-based fallback capabilities
        if goal in _GOAL_CAPABILITIES:
            caps.update(_GOAL_CAPABILITIES[goal])

        return sorted(caps)

    def check_availability(self, capabilities: list[str]) -> dict[str, bool]:
        """Check if each capability is available on the current system.

        Args:
            capabilities: List of capability strings to check.

        Returns:
            Dict mapping capability name to availability boolean.
        """
        system = platform.system().lower()
        result: dict[str, bool] = {}

        for cap in capabilities:
            if cap not in CAPABILITY_MAP:
                result[cap] = False
                continue
            result[cap] = self._is_capable(cap, system)

        return result

    def get_handler_for_capability(self, capability: str) -> str | None:
        """Return the default handler module path for a capability.

        Args:
            capability: Capability string (e.g. ``"browser"``).

        Returns:
            Dotted module path (e.g. ``"jarvis.tools.browser"``) or
            ``None`` if the capability is unknown.
        """
        cap_info = CAPABILITY_MAP.get(capability)
        if cap_info is None:
            return None
        return str(cap_info["handler"])

    def get_requirements(self, capability: str) -> list[str]:
        """Return the system requirements for a capability.

        Args:
            capability: Capability string.

        Returns:
            List of requirement strings, or empty list if unknown.
        """
        cap_info = CAPABILITY_MAP.get(capability)
        if cap_info is None:
            return []
        return list(cap_info["requirements"])  # type: ignore[arg-type]

    # ── internal helpers ────────────────────────────────────────────

    @staticmethod
    def _is_capable(capability: str, system: str) -> bool:
        """Heuristic check for a single capability on the current OS.

        Uses lightweight checks (import probes, platform detection)
        rather than actually launching services.
        """
        if capability == "browser":
            return system in ("windows", "linux", "darwin")

        if capability == "app_launcher":
            return system in ("windows", "linux", "darwin")

        if capability == "search_engine":
            return True  # always available if network exists

        if capability == "media_player":
            return True  # most OSes have media playback

        if capability == "system_control":
            return system in ("windows", "linux", "darwin")

        if capability == "file_system":
            return True  # universally available

        if capability == "memory":
            return True  # in-process storage

        if capability == "calculator":
            return True  # pure computation

        if capability == "network":
            try:
                importlib.import_module("urllib.request")
                return True
            except ImportError:
                return False

        if capability == "display":
            return system in ("windows", "linux", "darwin")

        if capability == "programming":
            return True  # code editors are available on all platforms

        if capability == "version_control":
            try:
                import subprocess
                result = subprocess.run(["git", "--version"], capture_output=True, timeout=5)
                return result.returncode == 0
            except Exception:
                return False

        if capability == "database":
            return True  # SQLite is always available

        if capability == "cloud":
            return True  # cloud APIs are network-based

        if capability == "ai_ml":
            try:
                importlib.import_module("numpy")
                return True
            except ImportError:
                return False

        if capability == "security":
            return system in ("windows", "linux", "darwin")

        if capability == "automation":
            return True  # scripting is always possible

        if capability == "data_analysis":
            try:
                importlib.import_module("pandas")
                return True
            except ImportError:
                return False

        if capability == "design":
            return True  # design tools are available

        if capability == "video_editing":
            return True  # video editors are available

        if capability == "audio_editing":
            return True  # audio editors are available

        if capability == "image_editing":
            return True  # image editors are available

        if capability == "3d_modeling":
            return True  # 3D tools are available

        if capability == "gaming":
            return True  # games are available

        if capability == "devops":
            try:
                import subprocess
                result = subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
                return result.returncode == 0
            except Exception:
                return False

        if capability == "testing":
            return True  # test frameworks are available

        if capability == "documentation":
            return True  # documentation tools are available

        if capability == "collaboration":
            return True  # collaboration tools are network-based

        if capability == "analytics":
            return True  # analytics tools are available

        return False
