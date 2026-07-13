"""Core registries and bootstrap utilities for the AI OS.

Keep this lightweight: registries for plugins, tools, agents and a
central bootstrap that wires components together. All AI calls must
use the `router_client` from `jarvis.router_service` (AI Router).
"""
from __future__ import annotations

from typing import Any, Callable, Dict
import logging

from jarvis import router_service

logger = logging.getLogger(__name__)


class AIOS:
    """Main AI OS facade.

    Responsibilities:
    - Register and discover plugins/tools/agents
    - Provide a central entrypoint for subsystems
    - Expose the router client for all subsystems
    """

    def __init__(self) -> None:
        self.router = router_service.router_client
        self._plugins: Dict[str, Any] = {}
        self._tools: Dict[str, Any] = {}
        self._agents: Dict[str, Any] = {}

    def register_plugin(self, name: str, plugin: Any) -> None:
        logger.info("Registering plugin %s", name)
        self._plugins[name] = plugin

    def get_plugin(self, name: str) -> Any | None:
        return self._plugins.get(name)

    def register_tool(self, name: str, tool: Any) -> None:
        logger.info("Registering tool %s", name)
        self._tools[name] = tool

    def get_tool(self, name: str) -> Any | None:
        return self._tools.get(name)

    def register_agent(self, name: str, agent: Any) -> None:
        logger.info("Registering agent %s", name)
        self._agents[name] = agent

    def get_agent(self, name: str) -> Any | None:
        return self._agents.get(name)


_ai_os: AIOS | None = None


def get_ai_os() -> AIOS:
    global _ai_os
    if _ai_os is None:
        _ai_os = AIOS()
    return _ai_os
