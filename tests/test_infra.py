"""Tests for Infrastructure Layer — All 10 modules.

Tests event bus, state manager, service registry, environment engine,
desktop intelligence, security layer, settings storage, benchmarks,
analytics, and centralized logging.
"""

import asyncio
import pytest
import time
import tempfile
import os
from pathlib import Path

from jarvis.infra.events import EventBus, EventType, Event, event_bus
from jarvis.infra.state import StateManager, state_manager
from jarvis.infra.services import ServiceRegistry, ServiceInfo, ServiceStatus, service_registry
from jarvis.infra.environment import EnvironmentEngine, SystemResources
from jarvis.infra.desktop import DesktopIntelligence, DesktopSession, SessionType, ActiveWindow
from jarvis.infra.security import SecurityLayer, SecurityPolicy, Permission, RiskLevel, AuditEntry
from jarvis.infra.settings import SettingsStorage, _DEFAULT_SETTINGS
from jarvis.infra.benchmarks import Benchmarking, BenchmarkEntry
from jarvis.infra.analytics import Analytics, UsageMetric
from jarvis.infra.logging_system import CentralizedLogger, LogLevel, LogEntry


# ═══════════════════════════════════════════════════════════════════════
# EVENT BUS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestEventBus:
    def setup_method(self):
        self.bus = EventBus()

    def test_emit_and_receive(self):
        received = []
        self.bus.on(EventType.APP_STARTED, lambda e: received.append(e))
        self.bus.emit(EventType.APP_STARTED, source="test")
        assert len(received) == 1
        assert received[0].source == "test"
        assert received[0].type == EventType.APP_STARTED

    def test_multiple_handlers(self):
        count = [0]
        self.bus.on(EventType.APP_STARTED, lambda e: count.__setitem__(0, count[0] + 1))
        self.bus.on(EventType.APP_STARTED, lambda e: count.__setitem__(0, count[0] + 1))
        self.bus.emit(EventType.APP_STARTED)
        assert count[0] == 2

    def test_unsubscribe(self):
        received = []
        handler = lambda e: received.append(e)
        self.bus.on(EventType.APP_STARTED, handler)
        self.bus.off(EventType.APP_STARTED, handler)
        self.bus.emit(EventType.APP_STARTED)
        assert len(received) == 0

    def test_wildcard_handler(self):
        received = []
        self.bus.on(None, lambda e: received.append(e))
        self.bus.emit(EventType.APP_STARTED)
        self.bus.emit(EventType.SPEECH_STARTED)
        assert len(received) == 2

    def test_event_data(self):
        received = []
        self.bus.on(EventType.CUSTOM, lambda e: received.append(e))
        self.bus.emit(EventType.CUSTOM, data={"key": "value"})
        assert received[0].data == {"key": "value"}

    def test_event_history(self):
        self.bus.emit(EventType.APP_STARTED)
        self.bus.emit(EventType.SPEECH_STARTED)
        history = self.bus.get_history()
        assert len(history) == 2

    def test_event_history_filtered(self):
        self.bus.emit(EventType.APP_STARTED)
        self.bus.emit(EventType.SPEECH_STARTED)
        history = self.bus.get_history(EventType.APP_STARTED)
        assert len(history) == 1

    def test_clear_history(self):
        self.bus.emit(EventType.APP_STARTED)
        self.bus.clear_history()
        assert len(self.bus.get_history()) == 0

    def test_handler_error_doesnt_crash(self):
        def bad_handler(e):
            raise ValueError("oops")
        self.bus.on(EventType.APP_STARTED, bad_handler)
        self.bus.emit(EventType.APP_STARTED)  # Should not raise

    def test_stats(self):
        self.bus.emit(EventType.APP_STARTED)
        stats = self.bus.get_stats()
        assert stats["total_events"] == 1

    def test_event_to_dict(self):
        event = Event(type=EventType.APP_STARTED, source="test", data={"a": 1})
        d = event.to_dict()
        assert d["type"] == "app.started"
        assert d["source"] == "test"


# ═══════════════════════════════════════════════════════════════════════
# STATE MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestStateManager:
    def setup_method(self):
        self.state = StateManager()

    def test_get_default(self):
        assert self.state.get("current_user") == "default"

    def test_set_and_get(self):
        self.state.set("current_project", "jarvis")
        assert self.state.get("current_project") == "jarvis"

    def test_get_many(self):
        values = self.state.get_many("current_user", "current_project")
        assert "current_user" in values
        assert "current_project" in values

    def test_set_many(self):
        self.state.set_many({"a": 1, "b": 2})
        assert self.state.get("a") == 1
        assert self.state.get("b") == 2

    def test_snapshot(self):
        snap = self.state.snapshot()
        assert isinstance(snap, dict)
        assert "current_user" in snap

    def test_history(self):
        self.state.set("test_key", "v1", notify=False)
        self.state.set("test_key", "v2", notify=False)
        history = self.state.get_history("test_key")
        assert len(history) == 2

    def test_reset(self):
        self.state.set("current_theme", "light", notify=False)
        self.state.reset("current_theme")
        assert self.state.get("current_theme") == "dark"

    def test_notification(self):
        received = []
        self.state._bus.on(EventType.SETTINGS_CHANGED, lambda e: received.append(e))
        self.state.set("current_theme", "light")
        assert len(received) == 1

    def test_stats(self):
        stats = self.state.get_stats()
        assert stats["keys"] > 0


# ═══════════════════════════════════════════════════════════════════════
# SERVICE REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestServiceRegistry:
    def setup_method(self):
        self.registry = ServiceRegistry()

    def test_register(self):
        self.registry.register("test_service", priority=10)
        info = self.registry.get("test_service")
        assert info is not None
        assert info.priority == 10

    def test_unregister(self):
        self.registry.register("test_service")
        self.registry.unregister("test_service")
        assert self.registry.get("test_service") is None

    def test_get_all(self):
        self.registry.register("a")
        self.registry.register("b")
        all_services = self.registry.get_all()
        assert len(all_services) == 2

    def test_get_sorted(self):
        self.registry.register("a", priority=30)
        self.registry.register("b", priority=10)
        self.registry.register("c", priority=20)
        sorted_names = self.registry.get_sorted()
        assert sorted_names == ["b", "c", "a"]

    def test_get_by_status(self):
        self.registry.register("test")
        info = self.registry.get("test")
        info.status = ServiceStatus.RUNNING
        running = self.registry.get_by_status(ServiceStatus.RUNNING)
        assert "test" in running

    def test_health(self):
        self.registry.register("a")
        self.registry.register("b")
        health = self.registry.get_health()
        assert health["total"] == 2

    def test_dependencies(self):
        self.registry.register("db", priority=1)
        self.registry.register("api", priority=2, dependencies=["db"])
        order = self.registry._get_start_order()
        assert order.index("db") < order.index("api")


# ═══════════════════════════════════════════════════════════════════════
# ENVIRONMENT ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestEnvironmentEngine:
    def setup_method(self):
        self.env = EnvironmentEngine(poll_interval=100)

    def test_snapshot(self):
        res = self.env.snapshot()
        assert isinstance(res, SystemResources)

    def test_performance_mode(self):
        res = SystemResources(cpu_percent=30, ram_percent=40)
        assert res.performance_mode == "balanced"

    def test_performance_mode_constrained(self):
        res = SystemResources(cpu_percent=90, ram_percent=95)
        assert res.performance_mode == "ultra_performance"

    def test_performance_mode_battery_saver(self):
        res = SystemResources(battery_percent=15, battery_charging=False)
        assert res.performance_mode == "battery_saver"

    def test_is_constrained(self):
        res = SystemResources(cpu_percent=85)
        assert res.is_constrained is True

    def test_get_setting(self):
        mode = self.env.get_setting("performance_mode")
        assert mode in ("balanced", "ultra_performance", "battery_saver")

    def test_to_dict(self):
        res = SystemResources(cpu_percent=50)
        d = res.to_dict()
        assert "cpu_percent" in d
        assert "performance_mode" in d

    def test_stats(self):
        self.env._collect_once()
        res = self.env.snapshot()
        assert res.platform != ""


# ═══════════════════════════════════════════════════════════════════════
# DESKTOP INTELLIGENCE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestDesktopIntelligence:
    def setup_method(self):
        self.di = DesktopIntelligence(poll_interval=100)

    def test_initial_session(self):
        session = self.di.current_session()
        assert isinstance(session, DesktopSession)

    def test_classify_coding(self):
        apps = ["code", "terminal", "github"]
        stype, conf = self.di._classify(apps, [])
        assert stype == SessionType.CODING
        assert conf > 0

    def test_classify_gaming(self):
        apps = ["steam", "discord"]
        stype, conf = self.di._classify(apps, [])
        assert stype == SessionType.GAMING

    def test_classify_browsing(self):
        apps = ["chrome"]
        stype, conf = self.di._classify(apps, [])
        assert stype == SessionType.BROWSING

    def test_classify_unknown(self):
        stype, conf = self.di._classify([], [])
        assert stype == SessionType.UNKNOWN

    def test_classify_study(self):
        apps = ["chrome", "notion"]
        stype, conf = self.di._classify(apps, [])
        assert stype == SessionType.STUDY

    def test_active_windows(self):
        windows = self.di.get_active_windows()
        assert isinstance(windows, list)

    def test_history(self):
        history = self.di.get_history()
        assert isinstance(history, list)


# ═══════════════════════════════════════════════════════════════════════
# SECURITY LAYER TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSecurityLayer:
    def setup_method(self):
        self.security = SecurityLayer()

    def test_store_and_get_secret(self):
        self.security.store_secret("TEST_KEY", "secret_value_123")
        assert self.security.get_secret("TEST_KEY") == "secret_value_123"

    def test_has_secret(self):
        self.security.store_secret("MY_KEY", "value")
        assert self.security.has_secret("MY_KEY") is True
        assert self.security.has_secret("NONEXISTENT") is False

    def test_remove_secret(self):
        self.security.store_secret("DEL_KEY", "value")
        self.security.remove_secret("DEL_KEY")
        assert self.security.has_secret("DEL_KEY") is False

    def test_is_sensitive(self):
        assert self.security.is_sensitive("password=secret123") is True
        assert self.security.is_sensitive("api_key=abc") is True
        assert self.security.is_sensitive("sk-abc123def456ghi789jkl") is True
        assert self.security.is_sensitive("hello world") is False

    def test_sanitize(self):
        text = "My sk-abc123def456ghi789jkl token and password xyz"
        sanitized = self.security.sanitize(text)
        assert "[REDACTED]" in sanitized

    def test_permissions(self):
        self.security.grant_permission("web", Permission.NETWORK)
        assert self.security.check_permission("web", Permission.NETWORK) is True
        assert self.security.check_permission("web", Permission.EXECUTE) is False

    def test_audit(self):
        entry = self.security.audit("tool_use", "web_search", Permission.TOOL_USE)
        assert entry.allowed is True
        assert entry.action == "tool_use"

    def test_needs_confirmation(self):
        assert self.security.needs_confirmation("system_command") is True
        assert self.security.needs_confirmation("read") is False

    def test_audit_log(self):
        self.security.audit("test", "resource1")
        self.security.audit("test", "resource2")
        log = self.security.get_audit_log(action="test")
        assert len(log) == 2

    def test_stats(self):
        stats = self.security.get_stats()
        assert "secrets_stored" in stats
        assert "audit_entries" in stats


# ═══════════════════════════════════════════════════════════════════════
# SETTINGS STORAGE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSettingsStorage:
    def setup_method(self):
        self.tmp = tempfile.mktemp(suffix=".json")
        self.settings = SettingsStorage(path=self.tmp)

    def teardown_method(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_get_default(self):
        assert self.settings.get("theme") == "dark"

    def test_set_and_get(self):
        self.settings.set("theme", "light")
        assert self.settings.get("theme") == "light"

    def test_set_many(self):
        self.settings.set_many({"a": 1, "b": 2})
        assert self.settings.get("a") == 1
        assert self.settings.get("b") == 2

    def test_all(self):
        all_settings = self.settings.all()
        assert isinstance(all_settings, dict)
        assert "theme" in all_settings

    def test_reset(self):
        self.settings.set("theme", "light")
        self.settings.reset("theme")
        assert self.settings.get("theme") == "dark"

    def test_save_and_load(self):
        self.settings.set("theme", "light")
        self.settings.save()
        loaded = SettingsStorage(path=self.tmp)
        assert loaded.get("theme") == "light"

    def test_on_change(self):
        changes = []
        self.settings.on_change(lambda k, o, n: changes.append((k, o, n)))
        self.settings.set("theme", "blue")
        assert len(changes) == 1
        assert changes[0] == ("theme", "dark", "blue")

    def test_get_path(self):
        path = self.settings.get_path()
        assert isinstance(path, str)

    def test_stats(self):
        stats = self.settings.get_stats()
        assert "keys" in stats


# ═══════════════════════════════════════════════════════════════════════
# BENCHMARKS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestBenchmarks:
    def setup_method(self):
        self.bench = Benchmarking()

    def test_record(self):
        self.bench.record("nlp", "process", 45.0)
        self.bench.record("nlp", "process", 55.0)
        stats = self.bench.get_subsystem("nlp")
        assert stats["samples"] == 2
        assert stats["avg_ms"] == 50.0

    def test_start_end(self):
        self.bench.start("router", "select")
        time.sleep(0.001)
        latency = self.bench.end("router", "select")
        assert latency > 0

    def test_get_all(self):
        self.bench.record("nlp", "process", 45.0)
        self.bench.record("router", "select", 5.0)
        all_bench = self.bench.get_all()
        assert "nlp" in all_bench
        assert "router" in all_bench

    def test_clear(self):
        self.bench.record("test", "op", 10.0)
        self.bench.clear()
        assert self.bench.get_total_entries() == 0

    def test_stats(self):
        self.bench.record("nlp", "process", 45.0)
        stats = self.bench.get_stats()
        assert stats["total_entries"] == 1

    def test_success_rate(self):
        self.bench.record("test", "op", 10.0, success=True)
        self.bench.record("test", "op", 10.0, success=True)
        stats = self.bench.get_subsystem("test")
        assert stats["success_rate"] == 1.0


# ═══════════════════════════════════════════════════════════════════════
# ANALYTICS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestAnalytics:
    def setup_method(self):
        self.analytics = Analytics()

    def test_track(self):
        self.analytics.track("tool", "web_search", value=150.0)
        count = self.analytics.count("tool", "web_search")
        assert count == 1

    def test_increment(self):
        self.analytics.increment("chat", "request")
        self.analytics.increment("chat", "request")
        assert self.analytics.count("chat", "request") == 2

    def test_get_summary(self):
        self.analytics.track("tool", "web_search")
        self.analytics.track("chat", "request")
        summary = self.analytics.get_summary()
        assert summary["total_events"] == 2

    def test_get_category(self):
        self.analytics.track("tool", "web_search")
        self.analytics.track("tool", "file_read")
        cat = self.analytics.get_category("tool")
        assert "web_search" in cat
        assert "file_read" in cat

    def test_get_recent(self):
        self.analytics.track("test", "event")
        recent = self.analytics.get_recent("test")
        assert len(recent) == 1

    def test_stats(self):
        stats = self.analytics.get_stats()
        assert "total_metrics" in stats


# ═══════════════════════════════════════════════════════════════════════
# CENTRALIZED LOGGING TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestCentralizedLogger:
    def setup_method(self):
        self.logger = CentralizedLogger()

    def test_info(self):
        self.logger.info("nlp", "Pipeline started")
        entries = self.logger.get_recent()
        assert len(entries) >= 1
        assert entries[-1].level == LogLevel.INFO

    def test_error(self):
        self.logger.error("router", "Failed", {"provider": "groq"})
        entries = self.logger.get_recent()
        assert entries[-1].level == LogLevel.ERROR

    def test_search(self):
        self.logger.info("nlp", "Pipeline started")
        self.logger.info("router", "Request sent")
        results = self.logger.search("pipeline")
        assert len(results) == 1

    def test_filter(self):
        self.logger.info("nlp", "msg1")
        self.logger.error("nlp", "msg2")
        self.logger.info("router", "msg3")
        errors = self.logger.filter(level=LogLevel.ERROR)
        assert len(errors) == 1

    def test_filter_by_subsystem(self):
        self.logger.info("nlp", "msg1")
        self.logger.info("router", "msg2")
        nlp_logs = self.logger.filter(subsystem="nlp")
        assert len(nlp_logs) == 1

    def test_get_subsystems(self):
        self.logger.info("nlp", "msg")
        self.logger.info("router", "msg")
        subsystems = self.logger.get_subsystems()
        assert "nlp" in subsystems

    def test_get_level_counts(self):
        self.logger.info("test", "msg")
        self.logger.error("test", "msg")
        counts = self.logger.get_level_counts()
        assert counts.get("info", 0) >= 1

    def test_export(self):
        self.logger.info("test", "export test")
        tmp = tempfile.mktemp(suffix=".json")
        count = self.logger.export(tmp)
        assert count >= 1
        os.remove(tmp)

    def test_clear(self):
        self.logger.info("test", "msg")
        self.logger.clear()
        assert len(self.logger.get_recent()) == 0

    def test_stats(self):
        self.logger.info("test", "msg")
        stats = self.logger.get_stats()
        assert stats["total_entries"] >= 1


# ═══════════════════════════════════════════════════════════════════════
# JARVIS APP TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestJARVISApp:
    def test_jarvis_import(self):
        from app import JARVIS
        jarvis = JARVIS()
        assert jarvis is not None

    def test_jarvis_has_infra(self):
        from app import JARVIS
        jarvis = JARVIS()
        assert jarvis.events is not None
        assert jarvis.state is not None
        assert jarvis.services is not None
        assert jarvis.settings is not None
        assert jarvis.security is not None
        assert jarvis.benchmarks is not None
        assert jarvis.analytics is not None
        assert jarvis.logger is not None

    def test_system_health(self):
        from app import JARVIS
        jarvis = JARVIS()
        health = jarvis.get_system_health()
        assert "boot_complete" in health
        assert "state" in health
        assert "services" in health
        assert "security" in health
        assert "settings" in health
        assert "benchmarks" in health
        assert "analytics" in health


# ═══════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
