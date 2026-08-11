"""tests/test_routing.py — Tests for JARVIS conversation vs tool routing.

Verifies that natural conversation, writing, translation, and knowledge
requests are handled by the LLM directly, and only actual external actions
trigger tool execution.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.planner import PlannerEngine
from core.tools_registry import UnifiedToolRegistry


planner = PlannerEngine()
registry = UnifiedToolRegistry()


# CONVERSATION -- must NOT trigger tools
CONVERSATION_NO_TOOLS = [
    "hello", "hi", "hey", "how are you?", "who are you?",
    "who created you?", "tell me something", "talk to me",
    "say something", "what do you think?", "do you know coding?",
    "can you speak Hindi?", "kya kar rahe ho?", "namaste",
    "good morning", "what's up",
    "don't use your tools, just talk normally",
    "don't use tool just talk",
    "without tools just answer",
    "skip tools and talk",
]

# WRITING -- must NOT trigger tools
WRITING_NO_TOOLS = [
    "write a 100 word essay on how AGI works",
    "write notes about Python",
    "write a story about a robot",
    "write Python code for a calculator",
    "write an email to my boss",
    "write a paragraph about climate change",
    "write a poem about nature",
    "write this in Hindi",
    "translate this to Bengali",
    "translate hello into Hindi, Bengali and Korean",
    "give me 20 languages",
    "write something in Korean",
    "write something in Hindi",
    "write something in Bengali",
    "generate a Python script",
    "create a to-do list",
    "compose a poem",
    "draft an email",
    "make a presentation",
]

# KNOWLEDGE -- must NOT trigger tools
KNOWLEDGE_NO_TOOLS = [
    "what is AGI?", "explain how Python works",
    "who invented the telephone?", "what is the capital of France?",
    "how does a computer work?", "why is the sky blue?",
    "tell me about machine learning", "describe quantum computing",
    "what is 2+2?", "define artificial intelligence",
    "meaning of algorithm", "how to learn Python",
    "who is Elon Musk?", "what happened today?",
    "is Python better than Java?",
]

# EXTERNAL ACTIONS -- MUST trigger tools
EXTERNAL_ACTION_TESTS = [
    ("open YouTube", "open_application"),
    ("open Chrome", "open_application"),
    ("launch Notepad", "open_application"),
    ("start Calculator", "open_application"),
    ("search Google for today's weather", "web_search"),
    ("google search Python tutorials", "web_search"),
    ("search web for machine learning", "web_search"),
    ("search YouTube for Minecraft", "youtube_search"),
    ("youtube search funny cats", "youtube_search"),
    ("find youtube videos about cooking", "youtube_search"),
    ("download youtube video https://youtube.com/watch?v=abc", "youtube_download"),
]

# MEMORY -- must use memory, not tools
MEMORY_NO_TOOLS = [
    "remember my sister's name is Nancy",
    "what is my sister's name?",
    "save my preference as dark mode",
    "what is my name?",
    "recall my project details",
    "don't forget my meeting at 3pm",
]

# EDGE CASES -- ambiguous, should NOT trigger tools
EDGE_CASE_NO_TOOLS = [
    "search my memory for something",
    "find out what AGI means",
    "look up the meaning of algorithm",
    "search for knowledge about Python",
    "can you find the answer?",
    "look up the definition",
    "search for information",
    "what are you looking for?",
    "find the solution",
    "search within your memory",
]

# MULTILINGUAL -- must NOT trigger tools
MULTILINGUAL_NO_TOOLS = [
    "talk in Hindi", "talk in Hinglish", "English bro",
    "korean mein bolo", "hindi mein jawab do",
    "Spanish mein baat karo", "speak in French",
]


def test_conversation_no_tools():
    for query in CONVERSATION_NO_TOOLS:
        plan = planner.build_plan(query)
        assert not plan.requires_tools, f"Planner set requires_tools for conversation: '{query}'"
        tool_name, _, _ = registry.classify_input(query)
        assert tool_name == "", f"Tool classified for conversation: '{query}' -> {tool_name}"
    print(f"PASSED: {len(CONVERSATION_NO_TOOLS)} conversation queries -> no tools")


def test_writing_no_tools():
    for query in WRITING_NO_TOOLS:
        plan = planner.build_plan(query)
        assert not plan.requires_tools, f"Planner set requires_tools for writing: '{query}'"
        tool_name, _, _ = registry.classify_input(query)
        assert tool_name == "", f"Tool classified for writing: '{query}' -> {tool_name}"
    print(f"PASSED: {len(WRITING_NO_TOOLS)} writing queries -> no tools")


def test_knowledge_no_tools():
    for query in KNOWLEDGE_NO_TOOLS:
        plan = planner.build_plan(query)
        assert not plan.requires_tools, f"Planner set requires_tools for knowledge: '{query}'"
        tool_name, _, _ = registry.classify_input(query)
        assert tool_name == "", f"Tool classified for knowledge: '{query}' -> {tool_name}"
    print(f"PASSED: {len(KNOWLEDGE_NO_TOOLS)} knowledge queries -> no tools")


def test_external_actions_trigger_tools():
    for query, expected_tool in EXTERNAL_ACTION_TESTS:
        plan = planner.build_plan(query)
        assert plan.requires_tools, f"Planner did NOT set requires_tools for: '{query}'"
        tool_name, arg_name, arg_value = registry.classify_input(query)
        assert tool_name == expected_tool, f"Wrong tool for '{query}': expected {expected_tool}, got {tool_name}"
        assert arg_value, f"No arg_value extracted for: '{query}'"
    print(f"PASSED: {len(EXTERNAL_ACTION_TESTS)} external actions -> correct tools")


def test_memory_no_tools():
    for query in MEMORY_NO_TOOLS:
        plan = planner.build_plan(query)
        assert not plan.requires_tools, f"Planner set requires_tools for memory: '{query}'"
        assert plan.requires_memory, f"Planner did NOT set requires_memory for: '{query}'"
        tool_name, _, _ = registry.classify_input(query)
        assert tool_name == "", f"Tool classified for memory: '{query}' -> {tool_name}"
    print(f"PASSED: {len(MEMORY_NO_TOOLS)} memory queries -> memory, no tools")


def test_edge_cases_no_tools():
    for query in EDGE_CASE_NO_TOOLS:
        tool_name, _, _ = registry.classify_input(query)
        assert tool_name == "", f"Tool classified for edge case: '{query}' -> {tool_name}"
    print(f"PASSED: {len(EDGE_CASE_NO_TOOLS)} edge cases -> no tools")


def test_multilingual_no_tools():
    for query in MULTILINGUAL_NO_TOOLS:
        plan = planner.build_plan(query)
        assert not plan.requires_tools, f"Planner set requires_tools for multilingual: '{query}'"
        tool_name, _, _ = registry.classify_input(query)
        assert tool_name == "", f"Tool classified for multilingual: '{query}' -> {tool_name}"
    print(f"PASSED: {len(MULTILINGUAL_NO_TOOLS)} multilingual queries -> no tools")


if __name__ == "__main__":
    print("=" * 60)
    print("JARVIS Routing Tests")
    print("=" * 60)
    print()
    test_conversation_no_tools()
    test_writing_no_tools()
    test_knowledge_no_tools()
    test_external_actions_trigger_tools()
    test_memory_no_tools()
    test_edge_cases_no_tools()
    test_multilingual_no_tools()
    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
