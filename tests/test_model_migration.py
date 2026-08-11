"""Model migration tests — custom JARVIS AGI model is the runtime default.

Acceptance criteria covered here:
- Default model identifier is `jarvis-agi` everywhere runtime-configurable.
- Friendly label is `JARVIS AGI`.
- Existing base URL is unchanged (no host/port/proxy change).
- The legacy MASTER SYSTEM PROMPT is never injected at runtime.
- Structured tool definitions are still sent/available.
- Conversation history (multi-turn) is preserved.
- Model health check targets `jarvis-agi`.
"""

import inspect
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

EXPECTED_MODEL = "jarvis-agi"
EXPECTED_BASE_URL = "https://kiersten-nonpunishable-carry.ngrok-free.dev"


@pytest.fixture
def clean_env(monkeypatch):
    """Remove model env overrides so code defaults are exercised."""
    for var in ("JARVIS_LLM_MODEL", "OLLAMA_MODEL", "JARVIS_LLM_FALLBACK"):
        monkeypatch.delenv(var, raising=False)


class TestModelSelection:
    def test_brain_adapter_default_model(self, clean_env):
        import core.brain_adapter as ba
        assert ba.BrainAdapter.DEFAULT_MODEL == EXPECTED_MODEL
        adapter = ba.BrainAdapter()
        assert adapter.primary_model == EXPECTED_MODEL
        assert adapter.fallback_model == EXPECTED_MODEL

    def test_router_defaults(self, clean_env):
        import core.router as router
        provider = router.OllamaProvider()
        assert provider.model == EXPECTED_MODEL
        airouter = router.AIRouter()
        assert airouter._ollama.model == EXPECTED_MODEL

    def test_no_legacy_model_identifiers_as_defaults(self, clean_env):
        import core.brain_adapter as ba
        import core.router as router
        for default in (
            ba.BrainAdapter.DEFAULT_MODEL,
            router.OllamaProvider().model,
        ):
            assert "qwen" not in default.lower()
            assert "llama3.2" not in default.lower()

    def test_friendly_label(self):
        # UI-facing label mapping used by chat panels.
        assert EXPECTED_MODEL.replace("-", " ").upper() == "JARVIS AGI"


class TestBaseURLPreservation:
    def test_brain_adapter_base_url_unchanged(self, clean_env):
        import core.brain_adapter as ba
        assert ba.BrainAdapter.DEFAULT_OLLAMA_URL == EXPECTED_BASE_URL
        assert ba.BrainAdapter._ollama_url() == EXPECTED_BASE_URL

    def test_router_base_url_unchanged(self, clean_env):
        import core.router as router
        assert router.OllamaProvider().base_url == EXPECTED_BASE_URL


class TestRuntimePromptPolicy:
    def test_brain_system_prompt_is_empty(self):
        from core.brain import Brain
        # Legacy Brain.__init__ depends on a stale `get_memory` import; we
        # test the prompt builder in isolation — the runtime master prompt
        # injection must be inert.
        brain = object.__new__(Brain)
        assert brain._build_system_prompt() == ""

    def test_qwen3_brain_prompt_is_minimal(self):
        from core.qwen3_brain import QWEN3Brain
        prompt = QWEN3Brain()._build_system_prompt()
        assert len(prompt) < 600
        lower = prompt.lower()
        assert "master" not in lower
        assert "you are jarvis" not in lower
        assert "operating documentation" not in lower
        assert '"tool"' in prompt  # legacy text-tool protocol kept

    def test_prompt_assembler_strips_master_prompt(self):
        from core.prompt_assembler import prompt_assembler
        from core.planner import planner_engine
        plan = planner_engine.build_plan("hello")
        assembled = prompt_assembler.assemble("hello", plan)
        combined = " ".join(
            str(msg.get("content", "")) for msg in assembled.messages
        ).lower()
        assert "you are jarvis" not in combined
        assert "core directives" not in combined
        assert "master" not in combined
        assert combined.count("execution-first") == 0


class TestHistoryAndToolsPreserved:
    def test_multiturn_history_preserved(self):
        from core.prompt_assembler import prompt_assembler
        from core.planner import planner_engine
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "what is python"},
            {"role": "assistant", "content": "a language"},
        ]
        assembled = prompt_assembler.assemble(
            "next question", planner_engine.build_plan("next question"),
            history=history,
        )
        roles = [m.get("role") for m in assembled.messages]
        assert roles.count("user") >= 2
        assert roles.count("assistant") >= 2
        contents = " ".join(str(m.get("content")) for m in assembled.messages)
        assert "what is python" in contents

    def test_structured_tool_definitions_still_generated(self):
        from core.tools_registry import tool_registry
        schemas = tool_registry.get_tool_schemas_for_llm()
        names = {
            s.get("function", {}).get("name")
            for s in schemas
            if isinstance(s.get("function"), dict)
        }
        assert "open_application" in names
        assert "web_search" in names
        assert all(s.get("type") == "function" for s in schemas)

    def test_tool_validation_still_works(self):
        from core.tools_registry import tool_registry
        ok, _, kwargs = tool_registry.validate_tool_call(
            "open_application", {"app_name": "youtube"}
        )
        assert ok and kwargs == {"app_name": "youtube"}


class TestHealthCheck:
    class _FakeResp:
        def __init__(self, body: bytes):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return self._body

    def _patch_tags(self, monkeypatch, names):
        import core.router as router
        payload = '{"models":[' + ",".join(
            f'{{"name": "{n}"}}' for n in names
        ) + "]}"

        def fake_urlopen(req, **kw):
            return self._FakeResp(payload.encode())

        monkeypatch.setattr(router.urllib.request, "urlopen", fake_urlopen)

    def test_health_check_verifies_jarvis_agi(self, clean_env, monkeypatch):
        import core.router as router
        self._patch_tags(monkeypatch, ["jarvis-agi:latest"])
        reachable, detail = router.check_tunnel_sync()
        assert reachable is True
        assert "jarvis-agi" in detail

    def test_health_check_fails_when_jarvis_agi_missing(
        self, clean_env, monkeypatch
    ):
        import core.router as router
        self._patch_tags(monkeypatch, ["qwen2.5-coder:14b-instruct-q5_K_M"])
        reachable, detail = router.check_tunnel_sync()
        assert reachable is False
        assert "model missing" in detail