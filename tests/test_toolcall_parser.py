"""ToolCallParser + ToolValidator tests — Tool Execution Contract.

Covers: native-styled JSON, JSON-as-text, malformed JSON, unknown tools,
invalid arguments, empty arguments, extra arguments, OpenAI-wrapped form,
and the guarantee that unknown JSON stays ordinary text.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.toolcall_parser import tool_call_parser, ToolCallParser
from core.tools_registry import tool_registry
from core.brain_adapter import ToolCall


class TestToolCallParsing:
    def test_json_tool_call(self):
        calls = tool_call_parser.parse_text(
            '{"name":"open_application","arguments":{"app_name":"youtube"}}'
        )
        assert len(calls) == 1
        assert calls[0].name == "open_application"
        assert calls[0].arguments == {"app_name": "youtube"}
        assert isinstance(calls[0], ToolCall)

    def test_json_with_call_id(self):
        calls = tool_call_parser.parse_text(
            '{"name":"web_search","arguments":{"query":"nasa mars"},'
            '"id":"call_xyz"}'
        )
        assert calls[0].call_id == "call_xyz"

    def test_openai_wrapped_json(self):
        calls = tool_call_parser.parse_text(
            '{"id":"call_1","type":"function","function":{'
            '"name":"web_search","arguments":"{\\"query\\": \\"cat pics\\"}"}}'
        )
        assert len(calls) == 1
        assert calls[0].name == "web_search"
        assert calls[0].arguments == {"query": "cat pics"}

    def test_json_array_multiple(self):
        calls = tool_call_parser.parse_text(
            '[{"name":"open_application","arguments":{"app_name":"youtube"}},'
            '{"name":"web_search","arguments":{"query":"gamerfleet"}}]'
        )
        assert [c.name for c in calls] == ["open_application", "web_search"]

    def test_embedded_json_with_chatter(self):
        calls = tool_call_parser.parse_text(
            'Sure, let me do that: {"name":"open_application",'
            '"arguments":{"app_name":"notepad"}}\nDone.'
        )
        assert len(calls) == 1
        assert calls[0].arguments == {"app_name": "notepad"}

    def test_json_in_code_fence(self):
        calls = tool_call_parser.parse_text(
            '```json\n{"name":"open_application","arguments":{"app_name":"chrome"}}\n```'
        )
        assert len(calls) == 1
        assert calls[0].arguments == {"app_name": "chrome"}

    def test_legacy_call_syntax_dict(self):
        calls = tool_call_parser.parse_text(
            'open_application({"app_name": "chrome"})'
        )
        assert len(calls) == 1
        assert calls[0].name == "open_application"
        assert calls[0].arguments == {"app_name": "chrome"}

    def test_legacy_call_syntax_string(self):
        calls = tool_call_parser.parse_text('open_application("chrome")')
        assert len(calls) == 1
        assert calls[0].arguments == {"app_name": "chrome"}

    def test_malformed_json_stays_text(self):
        calls = tool_call_parser.parse_text(
            '{"name":"open_application","arguments":{"app_name":'
        )
        assert calls == []

    def test_unknown_tool_stays_text(self):
        calls = tool_call_parser.parse_text(
            '{"name":"ghost_delete_files","arguments":{"file":"x"}}'
        )
        assert calls == []

    def test_invalid_arguments_stay_text(self):
        # required "app_name" missing
        calls = tool_call_parser.parse_text(
            '{"name":"open_application","arguments":{"wrong_key":"x"}}'
        )
        assert calls == []
        # wrong type entirely
        calls = tool_call_parser.parse_text(
            '{"name":"open_application","arguments":"not-an-object"}'
        )
        assert calls == []

    def test_empty_arguments(self):
        # nasa_apod takes no required arguments — empty args are valid
        calls = tool_call_parser.parse_text(
            '{"name":"nasa_apod","arguments":{}}'
        )
        assert len(calls) == 1 and calls[0].name == "nasa_apod"
        # open_application requires app_name — empty args invalid
        calls = tool_call_parser.parse_text(
            '{"name":"open_application","arguments":{}}'
        )
        assert calls == []

    def test_extra_arguments_stripped(self):
        calls = tool_call_parser.parse_text(
            '{"name":"open_application","arguments":'
            '{"app_name":"youtube","inject":{"bad":1}}}'
        )
        assert len(calls) == 1
        assert calls[0].arguments == {"app_name": "youtube"}

    def test_normal_conversation_never_parsed(self):
        samples = [
            "Hello! How can I help you today?",
            "The weather in London is rainy. The probability of rain is 80%.",
            'Python is a language where {} means a dictionary and {1: 2} exists.',
            'He said "name: open_application" but it was a joke.',
        ]
        for text in samples:
            assert tool_call_parser.parse_text(text) == [], text[:40]

    def test_duplicate_calls_deduplicated(self):
        calls = tool_call_parser.parse_text(
            '{"name":"open_application","arguments":{"app_name":"youtube"}}\n'
            '{"name":"open_application","arguments":{"app_name":"youtube"}}'
        )
        assert len(calls) == 1


class TestToolValidation:
    def test_registry_validate_ok(self):
        ok, reason, kwargs = tool_registry.validate_tool_call(
            "open_application", {"app_name": "youtube"}
        )
        assert ok and kwargs == {"app_name": "youtube"}

    def test_registry_validate_string_args(self):
        ok, reason, kwargs = tool_registry.validate_tool_call(
            "web_search", '{"query": "python"}'
        )
        assert ok and kwargs == {"query": "python"}

    def test_registry_validate_unknown(self):
        ok, reason, kwargs = tool_registry.validate_tool_call("ghost_tool", {})
        assert not ok and reason == "unknown_tool"

    def test_registry_validate_missing_required(self):
        ok, reason, _ = tool_registry.validate_tool_call("open_application", {})
        assert not ok and reason.startswith("missing_arguments")

    def test_registry_validate_extra_stripped(self):
        ok, _, kwargs = tool_registry.validate_tool_call(
            "open_application", {"app_name": "x", "evil": 1}
        )
        assert ok and kwargs == {"app_name": "x"}

    def test_parser_custom_registry(self):
        from core.tools_registry import UnifiedToolRegistry, ToolSpec

        reg = UnifiedToolRegistry()
        calls = ToolCallParser(registry=reg).parse_text(
            '{"name":"open_application","arguments":{"app_name":"youtube"}}'
        )
        assert len(calls) == 1