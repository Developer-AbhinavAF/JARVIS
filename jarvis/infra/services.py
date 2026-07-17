"""Service Registry — Service discovery and lifecycle management.

Every module registers as a service. The Runtime manages startup/shutdown.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from .events import EventBus, EventType, event_bus

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    REGISTERED = "registered"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """Metadata for a registered service."""
    name: str = ""
    status: ServiceStatus = ServiceStatus.REGISTERED
    priority: int = 50           # Lower = start first
    dependencies: list[str] = field(default_factory=list)
    health: float = 1.0
    started_at: float = 0.0
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


ServiceInit = Callable[[], Awaitable[None] | None]
ServiceShutdown = Callable[[], Awaitable[None] | None]


class ServiceRegistry:
    """Discovers and manages all JARVIS services.

    Usage:
        registry = ServiceRegistry()
        registry.register("nlp", init_fn=start_nlp, shutdown_fn=stop_nlp, priority=10)
        await registry.start_all()
        await registry.shutdown_all()
    """

    def __init__(self, bus: EventBus | None = None):
        self._services: dict[str, ServiceInfo] = {}
        self._init_fns: dict[str, ServiceInit] = {}
        self._shutdown_fns: dict[str, ServiceShutdown] = {}
        self._lock = threading.Lock()
        self._bus = bus or event_bus

    def register(
        self,
        name: str,
        init_fn: ServiceInit | None = None,
        shutdown_fn: ServiceShutdown | None = None,
        priority: int = 50,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        with self._lock:
            self._services[name] = ServiceInfo(
                name=name, priority=priority,
                dependencies=dependencies or [],
                metadata=metadata or {},
            )
            if init_fn:
                self._init_fns[name] = init_fn
            if shutdown_fn:
                self._shutdown_fns[name] = shutdown_fn

    def unregister(self, name: str):
        with self._lock:
            self._services.pop(name, None)
            self._init_fns.pop(name, None)
            self._shutdown_fns.pop(name, None)

    def get(self, name: str) -> ServiceInfo | None:
        return self._services.get(name)

    def get_all(self) -> dict[str, ServiceInfo]:
        return dict(self._services)

    def get_by_status(self, status: ServiceStatus) -> list[str]:
        return [name for name, s in self._services.items() if s.status == status]

    def get_sorted(self) -> list[str]:
        """Get service names sorted by priority (lower first)."""
        return sorted(self._services.keys(), key=lambda n: self._services[n].priority)

    async def start_all(self):
        """Start all services in priority order, respecting dependencies."""
        order = self._get_start_order()
        for name in order:
            await self.start_service(name)

    async def start_service(self, name: str):
        info = self._services.get(name)
        if not info or info.status == ServiceStatus.RUNNING:
            return

        # Check dependencies
        for dep in info.dependencies:
            dep_info = self._services.get(dep)
            if dep_info and dep_info.status != ServiceStatus.RUNNING:
                await self.start_service(dep)

        info.status = ServiceStatus.STARTING
        self._bus.emit(EventType.CUSTOM, source=f"service:{name}", data={"status": "starting"})

        init_fn = self._init_fns.get(name)
        if init_fn:
            try:
                result = init_fn()
                if hasattr(result, '__await__'):
                    await result
                info.status = ServiceStatus.RUNNING
                info.started_at = time.time()
                logger.info("Service %s started", name)
            except Exception as e:
                info.status = ServiceStatus.ERROR
                info.error = str(e)
                logger.error("Service %s failed: %s", name, e)
        else:
            info.status = ServiceStatus.RUNNING
            info.started_at = time.time()

        self._bus.emit(EventType.CUSTOM, source=f"service:{name}", data={"status": info.status.value})

    async def shutdown_all(self):
        """Shutdown all services in reverse priority order."""
        order = self.get_sorted()[::-1]
        for name in order:
            await self.shutdown_service(name)

    async def shutdown_service(self, name: str):
        info = self._services.get(name)
        if not info or info.status != ServiceStatus.RUNNING:
            return

        info.status = ServiceStatus.STOPPING
        shutdown_fn = self._shutdown_fns.get(name)
        if shutdown_fn:
            try:
                result = shutdown_fn()
                if hasattr(result, '__await__'):
                    await result
            except Exception as e:
                logger.warning("Service %s shutdown error: %s", name, e)

        info.status = ServiceStatus.STOPPED
        logger.info("Service %s stopped", name)

    def get_health(self) -> dict[str, Any]:
        running = len(self.get_by_status(ServiceStatus.RUNNING))
        total = len(self._services)
        return {
            "total": total,
            "running": running,
            "stopped": len(self.get_by_status(ServiceStatus.STOPPED)),
            "errors": len(self.get_by_status(ServiceStatus.ERROR)),
            "health": running / max(total, 1),
        }

    def _get_start_order(self) -> list[str]:
        """Topological sort respecting dependencies."""
        visited = set()
        order = []

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            info = self._services.get(name)
            if info:
                for dep in info.dependencies:
                    visit(dep)
            order.append(name)

        for name in self.get_sorted():
            visit(name)

        return order


# Global instance
service_registry = ServiceRegistry()

__all__ = ["ServiceRegistry", "ServiceInfo", "ServiceStatus", "service_registry"]
