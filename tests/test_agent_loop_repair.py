"""Agent loop repair tests — full process_stream pipeline with a stubbed brain.

Validates:
- native structured tool calls execute (not just print)
- JSON-as-text tool calls execute and are hidden from the user
- unknown/malformed JSON remains an LLM text response
- user sees a clean summary, never raw tool JSON
- multi-step chained tool calls execute in order
- tool failure is fed back to the LLM, which produces a sane response

NOTE: queries intentionally avoid the deterministic fast path ("can you
open X...") so the tests exercise the real agent loop.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json

import pytest

from core.jarvis_core import JarvisCore
from core.brain_adapter import LLMResult, ToolCall
from core.events import ExecutionEvent, VerificationEvent


def make_core(monkeypatch, brain_script, handler):
    """Build a JarvisCore with scripted brain + executor.

    brain_script(n_tool_results) -> LLMResult or generator
    handler(tool_name, kwargs)   -> structured result dict
    Returns (core, executed_log).
    """
    from core import tools_registry as tr_mod

    core = JarvisCore()
    core._booted = True

    executed = []

    def fake_execute(tool_name, **kwargs):
        executed.append((tool_name, dict(kwargs)))
        return handler(tool_name, kwargs)

    monkeypatch.setattr(tr_mod.tool_registry, "execute", fake_execute)

    async def fake_chat_with_tools(messages, tools=None, temperature=0.25,
                                   max_tokens=2048):
        n_tool_results = sum(1 for m in messages if m.get("role") == "tool")
        result = brain_script(n_tool_results)
        # Support both LLMResult and generator for streaming
        if asyncio.iscoroutine(result):
            result = await result
        if isinstance(result, LLMResult):
            return result
        # If brain_script returns a generator, collect it
        if hasattr(result, '__aiter__'):
            collected = ""
            async for chunk in result:
                collected += chunk
            return LLMResult(content=collected, done=True)
        return result

    async def fake_chat_stream(messages, model=None, temperature=0.25,
                               max_tokens=2048, tools=None, tool_call_sink=None):
        n_tool_results = sum(1 for m in messages if m.get("role") == "tool")
        result = brain_script(n_tool_results)
        # Support both LLMResult and generator for streaming
        if asyncio.iscoroutine(result):
            result = await result
        if isinstance(result, LLMResult):
            # If there are tool calls, collect them in the sink
            if result.tool_calls and tool_call_sink is not None:
                for idx, tc in enumerate(result.tool_calls):
                    tool_call_sink[idx] = {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                        "call_id": tc.call_id or "",
                    }
            # Stream the content
            for char in result.content:
                yield char
            return
        # If brain_script returns a generator, stream it
        if hasattr(result, '__aiter__'):
            async for chunk in result:
                yield chunk
            return
        # Stream the content
        for char in result.content:
            yield char

    monkeypatch.setattr(core.brain_adapter, "chat_with_tools",
                        fake_chat_with_tools)
    monkeypatch.setattr(core.brain_adapter, "chat_stream",
                        fake_chat_stream)
    monkeypatch.setattr(core.brain_adapter, "_flush_tool_call_slots",
                        lambda sink, target: target.extend([ToolCall(name=t.get("name"), arguments=json.loads(t.get("arguments", "{}")), call_id=t.get("call_id")) for t in sink.values()]))
    return core, executed


def drain(core, query):
    events = []

    async def run():
        async for ev in core.process_stream(query):
            events.append(ev)

    asyncio.run(run())
    return events


def final_of(events):
    for ev in events:
        if getattr(ev, "event_type", "") == "final_response":
            return getattr(ev, "text", "")
    return ""


def success_handler(tool, kwargs):
    if tool == "open_application":
        return {
            "success": True, "verified": True, "tool": tool,
            "output": f"Opened {kwargs.get('app_name', '')}.",
            "metadata": {"url_dispatched": True},
        }
    if tool == "web_search":
        return {
            "success": True, "verified": True, "tool": tool,
            "output": f"Searched for {kwargs.get('query', '')}.",
            "metadata": {"url": "https://google.com/search?q=x"},
        }
    return {"success": False, "verified": False, "tool": tool,
            "error": "unsupported"}


def failing_handler(tool, kwargs):
    return {"success": False, "verified": False, "tool": tool,
            "error": "app not available"}


class TestNativeToolCalls:
    def test_native_tool_call_executes_and_hides_json(self, monkeypatch):
        def brain_script(n_results):
            if n_results == 0:
                return LLMResult(
                    content="",
                    tool_calls=[ToolCall(
                        name="open_application",
                        arguments={"app_name": "youtube"}, call_id="c1")],
                    done=True,
                )
            return LLMResult(content="Opened YouTube.", done=True)

        core, executed = make_core(monkeypatch, brain_script, success_handler)
        events = drain(core, "can you open youtube for me please")

        assert executed == [("open_application", {"app_name": "youtube"})]
        assert sum(1 for e in events if isinstance(e, ExecutionEvent)) == 1
        assert sum(1 for e in events if isinstance(e, VerificationEvent)) == 1
        text = final_of(events)
        assert text == "Opened YouTube."
        assert "{" not in text
        assert "tool_call" not in text.lower()

    def test_two_native_tool_calls_run_in_order(self, monkeypatch):
        def brain_script(n_results):
            if n_results == 0:
                return LLMResult(
                    content="",
                    tool_calls=[
                        ToolCall(name="open_application",
                                 arguments={"app_name": "youtube"}),
                        ToolCall(name="web_search",
                                 arguments={"query": "gamerfleet"}),
                    ],
                    done=True,
                )
            return LLMResult(
                content="Opened YouTube and searched for gamerfleet.",
                done=True,
            )

        core, executed = make_core(monkeypatch, brain_script, success_handler)
        events = drain(core, "can you open youtube and search gamerfleet for me")

        assert executed == [
            ("open_application", {"app_name": "youtube"}),
            ("web_search", {"query": "gamerfleet"}),
        ]
        assert len([e for e in events if isinstance(e, ExecutionEvent)]) == 2
        text = final_of(events)
        assert text == "Opened YouTube and searched for gamerfleet."
        assert "{" not in text


class TestJsonAsText:
    def test_json_text_tool_call_executed_and_hidden(self, monkeypatch):
        def brain_script(n_results):
            if n_results == 0:
                return LLMResult(
                    content='{"name":"open_application",'
                            '"arguments":{"app_name":"notepad"}}',
                    done=True,
                )
            return LLMResult(content="Opened Notepad.", done=True)

        core, executed = make_core(monkeypatch, brain_script, success_handler)
        events = drain(core, "can you open notepad for me please")

        assert executed == [("open_application", {"app_name": "notepad"})]
        text = final_of(events)
        assert text == "Opened Notepad."
        assert "{" not in text
        assert "open_application" not in text

    def test_json_text_stringified_arguments(self, monkeypatch):
        def brain_script(n_results):
            if n_results == 0:
                return LLMResult(
                    content='{"name":"open_application","arguments":'
                            '"{\\"app_name\\": \\"youtube\\"}"}',
                    done=True,
                )
            return LLMResult(content="Opened YouTube.", done=True)

        core, executed = make_core(monkeypatch, brain_script, success_handler)
        events = drain(core, "can you open youtube please")

        assert executed == [("open_application", {"app_name": "youtube"})]
        assert final_of(events) == "Opened YouTube."
        assert "{" not in final_of(events)

    def test_chatty_json_text_with_fence(self, monkeypatch):
        def brain_script(n_results):
            if n_results == 0:
                return LLMResult(
                    content=(
                        "I will open that now:\n```json\n"
                        '{"name":"open_application",'
                        '"arguments":{"app_name":"chrome"}}\n```'
                    ),
                    done=True,
                )
            return LLMResult(content="Opened Chrome.", done=True)

        core, executed = make_core(monkeypatch, brain_script, success_handler)
        events = drain(core, "can you open chrome for me please")

        assert executed == [("open_application", {"app_name": "chrome"})]
        assert final_of(events) == "Opened Chrome."
        assert "{" not in final_of(events)

    def test_legacy_call_syntax(self, monkeypatch):
        def brain_script(n_results):
            if n_results == 0:
                return LLMResult(
                    content='Here you go: open_application({"app_name": "youtube"})',
                    done=True,
                )
            return LLMResult(content="Opened YouTube.", done=True)

        core, executed = make_core(monkeypatch, brain_script, success_handler)
        events = drain(core, "can you open youtube")

        assert executed == [("open_application", {"app_name": "youtube"})]
        assert final_of(events) == "Opened YouTube."

    def test_unknown_json_stays_response_text(self, monkeypatch):
        brain_script = lambda n: LLMResult(  # noqa: E731
            content='{"name":"invented_tool","arguments":{"x":1}}', done=True)

        core, executed = make_core(monkeypatch, brain_script, success_handler)
        events = drain(core, "can you open something weird for me")

        assert executed == []
        assert '"name":"invented_tool"' in final_of(events)

    def test_malformed_json_stays_response_text(self, monkeypatch):
        brain_script = lambda n: LLMResult(  # noqa: E731
            content='{"name":"open_application","arguments":{"app_name": "chrome"',
            done=True)

        core, executed = make_core(monkeypatch, brain_script, success_handler)
        events = drain(core, "can you open something for me")

        assert executed == []
        assert "chrome" in final_of(events)


class TestFailureHandling:
    def test_tool_failure_feeds_back_to_llm(self, monkeypatch):
        def brain_script(n_results):
            if n_results == 0:
                return LLMResult(
                    content="",
                    tool_calls=[ToolCall(
                        name="open_application",
                        arguments={"app_name": "vscode"})],
                    done=True,
                )
            return LLMResult(
                content="I couldn't open VS Code — the application looks "
                        "unavailable right now.",
                done=True,
            )

        core, executed = make_core(monkeypatch, brain_script, failing_handler)
        events = drain(core, "can you open vscode for me")

        assert executed == [("open_application", {"app_name": "vscode"})]
        text = final_of(events)
        assert "couldn't" in text.lower() or "unavailable" in text.lower()
        assert "traceback" not in text.lower()


class TestNoLeakGuarantee:
    @pytest.mark.parametrize("script", [
        lambda n: LLMResult(content='{"name":"open_application","arguments":{"app_name":"youtube"}}', done=True),
        lambda n: LLMResult(content='{"name":"open_application","arguments":"{\\"app_name\\": \\"youtube\\"}"}', done=True),
        lambda n: LLMResult(content='Here: open_application({"app_name": "youtube"})', done=True),
    ])
    def test_tool_json_never_rendered_as_final_response(self, monkeypatch, script):
        def always_ok(tool, kwargs):
            return {
                "success": True, "verified": True, "tool": tool,
                "output": f"Opened {kwargs.get('app_name', '')}.",
                "metadata": {"url_dispatched": True},
            }

        core, executed = make_core(monkeypatch, script, always_ok)
        events = drain(core, "can you open youtube for me")

        assert executed, "tool should have executed"
        text = final_of(events)
        assert "{" not in text
        assert "open_application" not in text