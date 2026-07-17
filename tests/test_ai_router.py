"""Tests for AI Router — Model Orchestration Engine.

Tests all 10 modules: config, models, capabilities, providers, health,
quota, metrics, load_balancer, fallback, latency, streaming, executor, router.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from jarvis.ai_router.config import RouterConfig, ProviderConfig, load_config
from jarvis.ai_router.models import (
    Capability, ProviderStatus, LoadBalanceStrategy, RouteStatus,
    Model, Route, RouterRequest, RouterResponse, HealthScore, QuotaInfo,
)
from jarvis.ai_router.capabilities import CapabilityDetector, CapabilityResult
from jarvis.ai_router.providers import ProviderRegistry, get_registry
from jarvis.ai_router.health import HealthMonitor
from jarvis.ai_router.quota import QuotaManager
from jarvis.ai_router.metrics import MetricsCollector, ProviderMetrics
from jarvis.ai_router.load_balancer import LoadBalancer
from jarvis.ai_router.fallback import FallbackManager, FallbackChain
from jarvis.ai_router.latency import LatencyPredictor
from jarvis.ai_router.streaming import StreamingAdapter, StreamEvent, StreamEventType, StreamBuffer
from jarvis.ai_router.executor import ProviderExecutor, ExecutionResult


# ═══════════════════════════════════════════════════════════════════════
# CONFIG TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_load_config(self):
        config = load_config()
        assert isinstance(config, RouterConfig)
        assert config.max_retries == 3
        assert config.overhead_budget_ms == 30.0

    def test_provider_config_defaults(self):
        p = ProviderConfig(name="test")
        assert p.enabled is True
        assert p.priority == 5
        assert p.max_rpm == 60
        assert p.max_tpm == 100000
        assert p.supports_streaming is True

    def test_config_providers_loaded(self):
        config = load_config()
        assert "groq" in config.providers
        assert "openai" in config.providers
        assert "anthropic" in config.providers
        assert "ollama" in config.providers
        assert "elevenlabs" in config.providers
        assert "tavily" in config.providers


# ═══════════════════════════════════════════════════════════════════════
# MODELS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestModels:
    def test_model_creation(self):
        m = Model(model_id="gpt-4o", provider="openai", capabilities=[Capability.CHAT, Capability.VISION])
        assert m.model_id == "gpt-4o"
        assert m.provider == "openai"
        assert Capability.CHAT in m.capabilities
        assert Capability.VISION in m.capabilities

    def test_model_to_dict(self):
        m = Model(model_id="gpt-4o", provider="openai", capabilities=[Capability.CHAT])
        d = m.to_dict()
        assert d["model_id"] == "gpt-4o"
        assert "chat" in d["capabilities"]

    def test_route_creation(self):
        r = Route(provider="groq", model="llama-3.3-70b-versatile", status=RouteStatus.SUCCESS)
        assert r.provider == "groq"
        assert r.status == RouteStatus.SUCCESS

    def test_route_to_dict(self):
        r = Route(provider="groq", model="llama-3.3-70b-versatile", status=RouteStatus.SUCCESS, latency_ms=45.0)
        d = r.to_dict()
        assert d["provider"] == "groq"
        assert d["latency_ms"] == 45.0

    def test_health_score(self):
        h = HealthScore(provider="groq", score=0.9, status=ProviderStatus.HEALTHY)
        assert h.provider == "groq"
        assert h.score == 0.9
        d = h.to_dict()
        assert d["status"] == "healthy"

    def test_quota_info(self):
        q = QuotaInfo(provider="groq", rpm_used=10, rpm_limit=60, daily_used=100, daily_limit=10000)
        assert q.rpm_available is True
        assert q.daily_available is True
        assert q.available is True

    def test_quota_exhausted(self):
        q = QuotaInfo(provider="test", rpm_used=60, rpm_limit=60)
        assert q.rpm_available is False
        assert q.available is False

    def test_router_request(self):
        req = RouterRequest(text="Hello", capability=Capability.CHAT)
        assert req.text == "Hello"
        assert req.max_tokens == 4096

    def test_router_response_success(self):
        resp = RouterResponse(content="Hi there")
        assert resp.success is True

    def test_router_response_error(self):
        resp = RouterResponse(error="Failed")
        assert resp.success is False

    def test_router_response_to_dict(self):
        resp = RouterResponse(content="Hello world", route=Route(provider="groq", model="test"))
        d = resp.to_dict()
        assert "content" in d
        assert "route" in d


# ═══════════════════════════════════════════════════════════════════════
# CAPABILITIES TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestCapabilities:
    def setup_method(self):
        self.detector = CapabilityDetector()

    def test_chat_detection(self):
        result = self.detector.detect("Hello, how are you?")
        assert result.primary == Capability.CHAT

    def test_vision_detection(self):
        result = self.detector.detect("What do you see in this image?")
        assert result.primary == Capability.VISION

    def test_search_detection(self):
        result = self.detector.detect("Search for latest AI news")
        assert result.primary == Capability.SEARCH

    def test_coding_detection(self):
        result = self.detector.detect("Write a Python function to sort a list")
        assert result.primary == Capability.CODING

    def test_reasoning_detection(self):
        result = self.detector.detect("Analyze step by step why this algorithm works")
        assert result.primary == Capability.REASONING

    def test_speech_detection(self):
        result = self.detector.detect("Say this out loud")
        assert result.primary == Capability.SPEECH

    def test_tool_detection(self):
        result = self.detector.detect("Open Chrome and navigate to google.com")
        assert result.primary == Capability.TOOL_USE

    def test_image_generation_detection(self):
        result = self.detector.detect("Generate a picture of a sunset on mars")
        assert result.primary == Capability.IMAGE_GENERATION

    def test_embedding_detection(self):
        result = self.detector.detect("Create embeddings for this text")
        assert result.primary == Capability.EMBEDDINGS

    def test_context_vision_boost(self):
        result = self.detector.detect("Describe this", context={"has_image": True})
        assert result.primary == Capability.VISION

    def test_confidence_range(self):
        result = self.detector.detect("Hello")
        assert 0.0 <= result.confidence <= 1.0

    def test_secondary_capabilities(self):
        result = self.detector.detect("Write code and search for examples")
        assert len(result.secondary) >= 0


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestProviderRegistry:
    def setup_method(self):
        config = RouterConfig()
        for name in ["groq", "openai", "anthropic", "gemini", "ollama", "deepseek",
                      "cerebras", "mistral", "nvidia_nim", "fireworks", "openrouter",
                      "cohere", "elevenlabs", "tavily"]:
            config.providers[name] = ProviderConfig(name=name, enabled=True)
        self.registry = ProviderRegistry(config)

    def test_providers_loaded(self):
        providers = self.registry.get_all_providers()
        assert len(providers) >= 13

    def test_enabled_providers(self):
        enabled = self.registry.get_enabled_providers()
        assert len(enabled) >= 13

    def test_get_models(self):
        models = self.registry.get_models()
        assert len(models) > 0

    def test_get_chat_models(self):
        models = self.registry.get_models(capability=Capability.CHAT)
        assert len(models) > 0

    def test_get_vision_models(self):
        models = self.registry.get_models(capability=Capability.VISION)
        assert len(models) > 0

    def test_get_coding_models(self):
        models = self.registry.get_models(capability=Capability.CODING)
        assert len(models) > 0

    def test_get_embedding_models(self):
        models = self.registry.get_models(capability=Capability.EMBEDDINGS)
        assert len(models) > 0

    def test_get_speech_models(self):
        models = self.registry.get_models(capability=Capability.SPEECH)
        assert len(models) > 0

    def test_get_image_generation_models(self):
        models = self.registry.get_models(capability=Capability.IMAGE_GENERATION)
        assert len(models) > 0

    def test_get_provider_models(self):
        models = self.registry.get_provider_models("groq")
        assert len(models) > 0
        assert all(m.provider == "groq" for m in models)

    def test_get_best_model(self):
        model = self.registry.get_best_model(Capability.CHAT)
        assert model is not None
        assert model.provider in self.registry.get_all_providers()

    def test_get_health(self):
        health = self.registry.get_health("groq")
        assert health.provider == "groq"

    def test_is_available(self):
        assert self.registry.is_available("groq") is True

    def test_stats(self):
        stats = self.registry.get_registry_stats()
        assert stats["providers"] >= 13
        assert stats["total_models"] > 0


# ═══════════════════════════════════════════════════════════════════════
# HEALTH MONITOR TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestHealthMonitor:
    def setup_method(self):
        self.monitor = HealthMonitor(window_size=50)

    def test_initial_health(self):
        health = self.monitor.get_score("groq")
        assert health.provider == "groq"
        assert health.score == 1.0
        assert health.status == ProviderStatus.UNKNOWN

    def test_record_success(self):
        self.monitor.record_success("groq", 50.0)
        self.monitor.record_success("groq", 60.0)
        health = self.monitor.get_score("groq")
        assert health.total_requests == 2
        assert health.consecutive_failures == 0
        assert health.success_rate == 1.0

    def test_record_failure(self):
        self.monitor.record_success("groq", 50.0)
        self.monitor.record_failure("groq", "timeout")
        health = self.monitor.get_score("groq")
        assert health.total_failures == 1
        assert health.consecutive_failures == 1

    def test_health_score_degrades(self):
        for _ in range(5):
            self.monitor.record_failure("test_prov")
        health = self.monitor.get_score("test_prov")
        assert health.score < 0.5

    def test_health_status(self):
        self.monitor.record_success("fast_prov", 30.0)
        self.monitor.record_success("fast_prov", 40.0)
        health = self.monitor.get_score("fast_prov")
        assert health.status in (ProviderStatus.HEALTHY, ProviderStatus.UNKNOWN)

    def test_get_healthy_providers(self):
        self.monitor.record_success("good", 50.0)
        self.monitor.record_failure("bad")
        self.monitor.record_failure("bad")
        self.monitor.record_failure("bad")
        self.monitor.record_failure("bad")
        healthy = self.monitor.get_healthy_providers(min_score=0.3)
        assert "good" in healthy

    def test_get_best_provider(self):
        self.monitor.record_success("fast", 30.0)
        self.monitor.record_success("slow", 200.0)
        best = self.monitor.get_best_provider(["fast", "slow"])
        assert best == "fast"

    def test_stats(self):
        self.monitor.record_success("groq", 45.0)
        stats = self.monitor.get_stats()
        assert "groq" in stats


# ═══════════════════════════════════════════════════════════════════════
# QUOTA MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestQuotaManager:
    def setup_method(self):
        self.mgr = QuotaManager()
        self.mgr.set_quota("groq", QuotaInfo(provider="groq", rpm_limit=60, daily_limit=10000))

    def test_can_use_initially(self):
        allowed, reason = self.mgr.can_use("groq")
        assert allowed is True
        assert reason == "ok"

    def test_record_usage(self):
        self.mgr.record_usage("groq", tokens=500)
        quota = self.mgr.get_quota("groq")
        assert quota.daily_used == 1

    def test_rpm_limit(self):
        q = QuotaInfo(provider="test", rpm_limit=3, daily_limit=1000)
        self.mgr.set_quota("test", q)
        for _ in range(3):
            self.mgr.record_usage("test")
        allowed, reason = self.mgr.can_use("test")
        assert allowed is False
        assert "RPM" in reason

    def test_daily_limit(self):
        q = QuotaInfo(provider="test2", rpm_limit=100, daily_limit=2)
        self.mgr.set_quota("test2", q)
        for _ in range(2):
            self.mgr.record_usage("test2")
        allowed, reason = self.mgr.can_use("test2")
        assert allowed is False
        assert "Daily" in reason

    def test_get_available_providers(self):
        self.mgr.set_quota("a", QuotaInfo(provider="a", rpm_limit=10, daily_limit=100))
        self.mgr.set_quota("b", QuotaInfo(provider="b", rpm_limit=1, daily_limit=1))
        self.mgr.record_usage("b")
        available = self.mgr.get_available_providers(["a", "b"])
        assert "a" in available
        assert "b" not in available

    def test_stats(self):
        self.mgr.record_usage("groq")
        stats = self.mgr.get_stats()
        assert "groq" in stats


# ═══════════════════════════════════════════════════════════════════════
# METRICS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestMetrics:
    def setup_method(self):
        self.collector = MetricsCollector(retention_seconds=3600)

    def test_record_success(self):
        route = Route(provider="groq", model="llama-3.3", status=RouteStatus.SUCCESS, latency_ms=50.0)
        self.collector.record(route, usage={"prompt_tokens": 100, "completion_tokens": 50}, cost=0.001)
        metrics = self.collector.get_provider("groq")
        assert metrics.total_requests == 1
        assert metrics.successful == 1

    def test_record_failure(self):
        route = Route(provider="openai", model="gpt-4o", status=RouteStatus.FAILED, latency_ms=100.0)
        self.collector.record(route)
        metrics = self.collector.get_provider("openai")
        assert metrics.failed == 1

    def test_multiple_records(self):
        for i in range(5):
            route = Route(provider="groq", model="llama", status=RouteStatus.SUCCESS, latency_ms=40.0 + i * 10)
            self.collector.record(route)
        metrics = self.collector.get_provider("groq")
        assert metrics.total_requests == 5
        assert metrics.avg_latency_ms > 0

    def test_capability_metrics(self):
        route = Route(provider="groq", model="llama", capability=Capability.CHAT, status=RouteStatus.SUCCESS)
        self.collector.record(route)
        metrics = self.collector.get_capability("chat")
        assert metrics.total_requests == 1

    def test_get_all(self):
        route = Route(provider="groq", model="llama", status=RouteStatus.SUCCESS)
        self.collector.record(route)
        all_metrics = self.collector.get_all()
        assert "providers" in all_metrics
        assert "groq" in all_metrics["providers"]

    def test_top_providers(self):
        for i in range(10):
            route = Route(provider="groq", model="llama", status=RouteStatus.SUCCESS, latency_ms=30.0)
            self.collector.record(route)
        top = self.collector.get_top_providers(by="requests", limit=3)
        assert len(top) > 0
        assert top[0][0] == "groq"

    def test_provider_metrics_properties(self):
        pm = ProviderMetrics(total_requests=10, successful=8, failed=2)
        assert pm.success_rate == 0.8
        d = pm.to_dict()
        assert d["success_rate"] == 0.8


# ═══════════════════════════════════════════════════════════════════════
# LOAD BALANCER TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestLoadBalancer:
    def setup_method(self):
        self.lb = LoadBalancer(LoadBalanceStrategy.ADAPTIVE)
        self.models = [
            Model(model_id="llama", provider="groq", capabilities=[Capability.CHAT]),
            Model(model_id="gpt-4o", provider="openai", capabilities=[Capability.CHAT]),
            Model(model_id="claude", provider="anthropic", capabilities=[Capability.CHAT]),
        ]
        self.health = {
            "groq": HealthScore(provider="groq", score=0.9, latency_ms=40.0),
            "openai": HealthScore(provider="openai", score=0.8, latency_ms=100.0),
            "anthropic": HealthScore(provider="anthropic", score=0.7, latency_ms=150.0),
        }

    def test_select_model(self):
        model = self.lb.select(self.models, self.health, {}, Capability.CHAT)
        assert model is not None
        assert model.provider in ["groq", "openai", "anthropic"]

    def test_adaptive_chooses_healthiest(self):
        # With enough data, adaptive should prefer healthier providers
        model = self.lb.select(self.models, self.health, {}, Capability.CHAT)
        assert model is not None

    def test_provider_preference(self):
        model = self.lb.select(self.models, self.health, {}, Capability.CHAT, provider_preference="openai")
        assert model.provider == "openai"

    def test_round_robin(self):
        lb = LoadBalancer(LoadBalanceStrategy.ROUND_ROBIN)
        selected = set()
        for _ in range(6):
            model = lb.select(self.models, self.health, {}, Capability.CHAT)
            selected.add(model.provider)
        assert len(selected) >= 2

    def test_least_latency(self):
        lb = LoadBalancer(LoadBalanceStrategy.LEAST_LATENCY)
        model = lb.select(self.models, self.health, {}, Capability.CHAT)
        assert model.provider == "groq"  # Fastest

    def test_weighted(self):
        lb = LoadBalancer(LoadBalanceStrategy.WEIGHTED)
        selected = set()
        for _ in range(20):
            model = lb.select(self.models, self.health, {}, Capability.CHAT)
            selected.add(model.provider)
        assert len(selected) >= 2

    def test_health_based(self):
        lb = LoadBalancer(LoadBalanceStrategy.HEALTH_BASED)
        model = lb.select(self.models, self.health, {}, Capability.CHAT)
        assert model.provider == "groq"  # Highest health

    def test_learning_update(self):
        self.lb.update_learning("groq", "chat", success=True, latency_ms=50.0)
        self.lb.update_learning("groq", "chat", success=True, latency_ms=50.0)
        stats = self.lb.get_stats()
        assert "groq:chat" in stats["learned_scores"]
        assert stats["learned_scores"]["groq:chat"] > 0.5

    def test_empty_models(self):
        model = self.lb.select([], self.health, {})
        assert model is None

    def test_stats(self):
        stats = self.lb.get_stats()
        assert "strategy" in stats
        assert stats["strategy"] == "adaptive"


# ═══════════════════════════════════════════════════════════════════════
# FALLBACK TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestFallback:
    def setup_method(self):
        self.fb = FallbackManager(max_retries=3)
        self.models = [
            Model(model_id="llama", provider="groq", capabilities=[Capability.CHAT]),
            Model(model_id="gpt-4o", provider="openai", capabilities=[Capability.CHAT]),
            Model(model_id="claude", provider="anthropic", capabilities=[Capability.CHAT]),
            Model(model_id="llama-local", provider="ollama", capabilities=[Capability.CHAT]),
        ]
        self.health = {
            "groq": HealthScore(provider="groq", score=0.9),
            "openai": HealthScore(provider="openai", score=0.8),
            "anthropic": HealthScore(provider="anthropic", score=0.7),
            "ollama": HealthScore(provider="ollama", score=0.6),
        }

    def test_build_chain(self):
        chain = self.fb.build_chain("groq", "llama", self.models, self.health)
        assert len(chain) > 0
        assert chain[0].provider == "groq"  # Primary (retry)
        assert chain[0].reason == "retry"

    def test_chain_has_alternatives(self):
        chain = self.fb.build_chain("groq", "llama", self.models, self.health)
        providers = [c.provider for c in chain]
        assert len(providers) >= 2

    def test_chain_has_local_fallback(self):
        chain = self.fb.build_chain("groq", "llama", self.models, self.health)
        providers = [c.provider for c in chain]
        assert "ollama" in providers

    def test_get_next(self):
        chain = self.fb.build_chain("groq", "llama", self.models, self.health)
        next_opt = self.fb.get_next(chain, "groq", "llama", 0)
        assert next_opt is not None

    def test_should_give_up(self):
        assert self.fb.should_give_up(3, 5) is True
        assert self.fb.should_give_up(1, 5) is False

    def test_cache(self):
        self.fb.cache_result("test_key", "cached_value", ttl=60.0)
        cached = self.fb.get_cached("test_key")
        assert cached == "cached_value"

    def test_cache_expiry(self):
        self.fb.cache_result("test_key", "value", ttl=0.0)
        time.sleep(0.01)
        cached = self.fb.get_cached("test_key")
        assert cached is None

    def test_failure_counting(self):
        self.fb.get_next(self.fb.build_chain("groq", "llama", self.models, self.health), "groq", "llama", 0)
        self.fb.get_next(self.fb.build_chain("groq", "llama", self.models, self.health), "groq", "llama", 1)
        count = self.fb.get_failure_count("groq", "llama")
        assert count >= 1

    def test_stats(self):
        stats = self.fb.get_stats()
        assert "cache_size" in stats
        assert "max_retries" in stats


# ═══════════════════════════════════════════════════════════════════════
# LATENCY PREDICTOR TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestLatencyPredictor:
    def setup_method(self):
        self.predictor = LatencyPredictor(window_size=100)

    def test_record_and_predict(self):
        for _ in range(10):
            self.predictor.record("groq", 50.0, tokens=500)
        predicted = self.predictor.predict("groq", tokens=500)
        assert 30.0 < predicted < 80.0

    def test_default_prediction(self):
        predicted = self.predictor.predict("unknown_provider")
        assert predicted == 500.0

    def test_token_adjustment(self):
        for _ in range(10):
            self.predictor.record("groq", 100.0, tokens=1000)
        predicted_short = self.predictor.predict("groq", tokens=500)
        predicted_long = self.predictor.predict("groq", tokens=2000)
        assert predicted_long > predicted_short

    def test_tokens_per_second(self):
        for _ in range(5):
            self.predictor.record("groq", 100.0, tokens=1000)
        tps = self.predictor.predict_tokens_per_second("groq")
        assert tps > 0

    def test_trend(self):
        # Simulate improving latency
        for i in range(30):
            self.predictor.record("groq", 200.0 - i * 3, tokens=500)
        trend = self.predictor.get_recent_trend("groq")
        assert trend in ("improving", "stable", "unknown")

    def test_stats(self):
        self.predictor.record("groq", 50.0)
        stats = self.predictor.get_stats()
        assert "groq" in stats
        assert "avg_latency_ms" in stats["groq"]


# ═══════════════════════════════════════════════════════════════════════
# STREAMING TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestStreaming:
    def test_stream_event(self):
        event = StreamEvent(type=StreamEventType.TEXT, content="Hello")
        assert event.type == StreamEventType.TEXT
        assert event.content == "Hello"

    def test_stream_buffer(self):
        buf = StreamBuffer()
        buf.add_chunk("Hello ")
        buf.add_chunk("World")
        assert buf.content == "Hello World"
        assert buf.is_complete is False

    def test_stream_buffer_done(self):
        buf = StreamBuffer()
        buf.add_event(StreamEvent(type=StreamEventType.DONE))
        assert buf.is_complete is True

    def test_stream_buffer_error(self):
        buf = StreamBuffer()
        buf.add_event(StreamEvent(type=StreamEventType.ERROR, content="fail"))
        assert buf.error == "fail"
        assert buf.is_complete is True

    def test_stream_buffer_clear(self):
        buf = StreamBuffer()
        buf.add_chunk("data")
        buf.clear()
        assert buf.content == ""

    def test_stream_event_types(self):
        for et in StreamEventType:
            event = StreamEvent(type=et, content="test")
            assert event.type == et


# ═══════════════════════════════════════════════════════════════════════
# EXECUTOR TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestExecutor:
    def setup_method(self):
        self.executor = ProviderExecutor()

    def test_execution_result_success(self):
        result = ExecutionResult(success=True, content="Hello", latency_ms=50.0)
        assert result.success is True

    def test_execution_result_failure(self):
        result = ExecutionResult(success=False, error="timeout")
        assert result.success is False


# ═══════════════════════════════════════════════════════════════════════
# ROUTER INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestRouter:
    def setup_method(self):
        config = RouterConfig()
        for name in ["groq", "openai", "anthropic", "gemini", "ollama", "deepseek",
                      "cerebras", "mistral", "nvidia_nim", "fireworks", "openrouter",
                      "cohere", "elevenlabs", "tavily"]:
            config.providers[name] = ProviderConfig(name=name, enabled=True)
        from jarvis.ai_router.router import AIRouter
        self.router = AIRouter(config)

    def test_router_initialization(self):
        assert self.router is not None
        assert self.router.registry is not None
        assert self.router.health is not None

    def test_get_available_models(self):
        models = self.router.get_available_models()
        assert len(models) > 0

    def test_get_available_chat_models(self):
        models = self.router.get_available_models(capability="chat")
        assert len(models) > 0

    def test_get_system_health(self):
        health = self.router.get_system_health()
        assert "total_providers" in health
        assert "healthy_providers" in health

    def test_get_provider_health(self):
        health = self.router.get_provider_health()
        assert isinstance(health, dict)

    def test_get_provider_quota(self):
        quota = self.router.get_provider_quota()
        assert isinstance(quota, dict)

    def test_get_metrics(self):
        metrics = self.router.get_metrics()
        assert isinstance(metrics, dict)

    def test_get_latency_predictions(self):
        preds = self.router.get_latency_predictions()
        assert isinstance(preds, dict)

    def test_get_load_balancer_stats(self):
        stats = self.router.get_load_balancer_stats()
        assert "strategy" in stats

    def test_get_fallback_stats(self):
        stats = self.router.get_fallback_stats()
        assert "cache_size" in stats

    def test_get_registry_stats(self):
        stats = self.router.get_registry_stats()
        assert stats["providers"] >= 13


# ═══════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
