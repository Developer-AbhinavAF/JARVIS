"""Resource independence tests.

Under simulated extreme load (CPU=100%, RAM=100%), normal requests MUST
still produce full, normal responses; resource values must never enter
prompt context; the system monitor must never control the conversation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

import pytest

from core.jarvis_core import JarvisCore
from core.brain_adapter import LLMResult
from core.events import ExecutionEvent


ESSAY = (
    "Artificial intelligence does not think the way humans do. "
    "A neural network processes patterns through layered math, adjusting "
    "weights in response to training data. There is no inner voice, no "
    "consciousness — yet across billions of parameters, something emerges "
    "that looks like reasoning. When a model writes an essay, it is "
    "distributing probability over tokens, choosing the next word from a "
    "landscape shaped by the texts it has seen. That is both powerful and "
    "strange: it can compose poetry it never memorized and fabricate facts "
    "it was never taught. AI thinks, therefore, in statistics rather than "
    "certainty, in correlation rather than belief, in prediction rather "
    "than understanding. The essay continues exploring this difference "
    "across many more sentences to demonstrate the full length of a "
    "generated response that the model must produce regardless of system "
    "load anywhere on the machine."
)


@pytest.fixture
def saturated_cpu(monkeypatch):
    """JarvisCore with resources pegged at 100% and a stubbed brain."""

    core = JarvisCore()
    core._booted = True  # skip diagnostics/warmup

    monkeypatch.setattr(
        "core.performance_manager.PerformanceManager.check_system_load",
        lambda self: {"cpu_percent": 100.0, "ram_percent": 100.0},
    )

    async def fake_chat_with_tools(messages, tools=None, temperature=0.25,
                                   max_tokens=2048):
        return LLMResult(content=ESSAY, tool_calls=[], done=True)

    monkeypatch.setattr(core.brain_adapter, "chat_with_tools",
                        fake_chat_with_tools)
    return core


def drain(core, query):
    events = []

    async def run():
        async for ev in core.process_stream(query):
            events.append(ev)

    asyncio.run(run())
    return events


def final_text(events):
    for ev in events:
        if getattr(ev, "event_type", "") == "final_response":
            return getattr(ev, "text", "")
    return ""


class TestResourceIndependence:
    def test_adapt_parameters_never_throttles(self, saturated_cpu):
        import core.performance_manager as pm
        assert pm.performance_manager.adapt_parameters(4096, 4) == (4096, 4)

    def test_essay_generated_at_100_percent_cpu(self, saturated_cpu):
        events = drain(saturated_cpu,
                       "bro write a 400 word essay on how AI thinks")
        text = final_text(events)
        assert text and len(text) > 100
        import re as _re
        assert not _re.search(r"\b(cpu|ram|memory|resource|refus)\b",
                              text.lower())

    def test_hello_normal_greeting_at_100_percent_cpu(self, saturated_cpu):
        events = drain(saturated_cpu, "hello")
        assert final_text(events) == ESSAY  # normal pipeline output unchanged

    def test_normal_conversation_no_execution_events(self, saturated_cpu):
        events = drain(saturated_cpu, "how are you")
        assert all(
            not isinstance(e, ExecutionEvent)
            for e in events
        )

    def test_normal_conversation_no_resource_talk(self, saturated_cpu):
        events = drain(saturated_cpu, "explain black holes simply")
        text = final_text(events)
        assert text == ESSAY
        assert "cpu" not in text.lower()
        assert "can't assist" not in text.lower()

    def test_memory_context_has_no_resource_food(self, saturated_cpu):
        # The assembled system prompt must never contain resource values.
        import re as _re
        from core.prompt_assembler import prompt_assembler
        from core.planner import planner_engine
        plan = planner_engine.build_plan("hello")
        assembled = prompt_assembler.assemble("hello", plan)
        combined = " ".join(
            str(msg.get("content", ""))
            for msg in assembled.messages
        ).lower()
        assert not _re.search(r"\bcpu\b|\bram\b|\bmemory usage\b", combined)


def test_desktop_food_has_no_resource_values():
    """get_desktop_food() must never inject CPU/RAM into chat context."""
    import importlib.util
    import pathlib

    backend = (pathlib.Path(__file__).parent.parent
               / "jarvis-desktop" / "backend" / "app.py")
    spec = importlib.util.spec_from_file_location("jarvis_desktop_backend",
                                                  backend)
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as exc:  # heavy import tree unavailable in CI env
        pytest.skip(f"backend import unavailable here: {exc}")

    food = mod.get_desktop_food()
    low = food.lower()
    assert "cpu" not in low and "memory" not in low and "ram" not in low
    assert "jarvis" in low


def test_system_status_only_when_asked():
    """Resource status tool fires ONLY on explicit requests."""
    from core.tools_registry import tool_registry
    assert tool_registry.route_fast_path("what is my CPU usage") is not None
    assert tool_registry.route_fast_path("system status") is not None
    assert tool_registry.route_fast_path("hello") is None
    assert tool_registry.route_fast_path("write an essay") is None