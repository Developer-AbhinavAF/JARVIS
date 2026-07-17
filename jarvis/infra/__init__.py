"""Infrastructure Layer — Connects every subsystem into one unified intelligence.

Modules:
- events: Event bus (pub/sub)
- state: State manager
- services: Service registry & lifecycle
- environment: System resource monitoring
- desktop: Desktop session detection
- security: API key protection, permissions, audit
- settings: Persistent JSON settings
- benchmarks: Performance tracking
- analytics: Usage statistics
- logging_system: Centralized searchable logs
"""

from .events import EventBus, EventType, Event, event_bus
from .state import StateManager, state_manager
from .services import ServiceRegistry, ServiceInfo, ServiceStatus, service_registry
from .environment import EnvironmentEngine, SystemResources, environment_engine
from .desktop import DesktopIntelligence, DesktopSession, SessionType, ActiveWindow, desktop_intelligence
from .security import SecurityLayer, SecurityPolicy, Permission, RiskLevel, AuditEntry, security_layer
from .settings import SettingsStorage, settings_storage, _DEFAULT_SETTINGS
from .benchmarks import Benchmarking, BenchmarkEntry, benchmarking
from .analytics import Analytics, UsageMetric, analytics
from .logging_system import CentralizedLogger, LogLevel, LogEntry, central_logger

__all__ = [
    # Events
    "EventBus", "EventType", "Event", "event_bus",
    # State
    "StateManager", "state_manager",
    # Services
    "ServiceRegistry", "ServiceInfo", "ServiceStatus", "service_registry",
    # Environment
    "EnvironmentEngine", "SystemResources", "environment_engine",
    # Desktop
    "DesktopIntelligence", "DesktopSession", "SessionType", "ActiveWindow", "desktop_intelligence",
    # Security
    "SecurityLayer", "SecurityPolicy", "Permission", "RiskLevel", "AuditEntry", "security_layer",
    # Settings
    "SettingsStorage", "settings_storage", "_DEFAULT_SETTINGS",
    # Benchmarks
    "Benchmarking", "BenchmarkEntry", "benchmarking",
    # Analytics
    "Analytics", "UsageMetric", "analytics",
    # Logging
    "CentralizedLogger", "LogLevel", "LogEntry", "central_logger",
]
