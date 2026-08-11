"""tests/test_memory_pipeline.py — Persistent memory write/retrieve contract.

Covers: explicit saves, paraphrase (semantic-ish) retrieval, persistence
across instances, supersession, deduplication, empty retrieval, honest
failures, extraction, legacy migration and the registry memory tools.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core.tools_registry as tr
from core.memory import UnifiedMemory, extract_memory_intent
from core.toolcall_parser import tool_call_parser


def _active(entries):
    return [e for e in entries if e.get("active")]


# ---------------------------------------------------------------------------
# EXPLICIT SAVE -> RETRIEVE
# ---------------------------------------------------------------------------

def test_explicit_save_then_exact_retrieve(tmp_path):
    mem = UnifiedMemory(str(tmp_path))
    intent = extract_memory_intent("remember that my favorite editor is VS Code")
    assert intent is not None
    result = mem.store(
        content=intent["content"],
        memory_type=intent["memory_type"],
        key=intent.get("key"),
        value=intent.get("value"),
        explicit=intent["explicit"],
    )
    assert result["success"] is True
    assert result["stored"] is True
    assert result["memory_id"]

    found = mem.retrieve("what is my favorite editor?", top_k=3)
    assert found, "Expected a match for 'what is my favorite editor?'"
    best = found[0]
    assert "VS Code" in str(best.get("value") or best.get("content"))


def test_search_single_hit_compat(tmp_path):
    mem = UnifiedMemory(str(tmp_path))
    mem.store(
        content="My favorite language is Python",
        memory_type="preference",
        key="favorite language",
        value="Python",
        explicit=True,
    )
    hit = mem.search("what is my favorite language?")
    assert hit is not None
    assert "Python" in hit


# ---------------------------------------------------------------------------
# PARAPHRASE RETRIEVAL
# ---------------------------------------------------------------------------

def test_paraphrase_retrieval(tmp_path):
    mem = UnifiedMemory(str(tmp_path))
    mem.store(content="I use VS Code for coding", memory_type="fact")
    found = mem.retrieve("which editor do I code with?", top_k=3)
    assert found, "Paraphrase query must still retrieve the memory"
    best = found[0]
    assert "VS Code" in str(best.get("value") or best.get("content"))


def test_memory_query_understanding(tmp_path):
    mem = UnifiedMemory(str(tmp_path))
    mem.store(
        content="My favorite editor is VS Code",
        memory_type="preference",
        key="favorite editor",
        value="VS Code",
        explicit=True,
    )
    for query in (
        "what is my favorite editor?",
        "which editor do I prefer?",
        "what code editor do I use?",
        "what editor did I say I liked?",
    ):
        found = mem.retrieve(query, top_k=3)
        assert found, f"No retrieval for: {query}"
        best = found[0]
        assert (
            best.get("key") == "favorite editor"
            or "VS Code" in str(best.get("value") or best.get("content"))
        ), f"Wrong memory for: {query}"


# ---------------------------------------------------------------------------
# PERSISTENCE (survives restart)
# ---------------------------------------------------------------------------

def test_persistence_across_instances(tmp_path):
    mem1 = UnifiedMemory(str(tmp_path))
    mem1.store(
        content="My brother's name is Alex",
        memory_type="relationship",
        key="brother's name",
        value="Alex",
        explicit=True,
    )

    mem2 = UnifiedMemory(str(tmp_path))
    found = mem2.retrieve("what is my brother's name?", top_k=3)
    assert found
    assert "Alex" in str(found[0].get("value") or found[0].get("content"))


# ---------------------------------------------------------------------------
# SUPERSESSION (new fact replaces old)
# ---------------------------------------------------------------------------

def test_update_supersedes_stale_fact(tmp_path):
    mem = UnifiedMemory(str(tmp_path))
    r1 = mem.store(
        content="My favorite editor is VS Code",
        memory_type="preference",
        key="favorite editor",
        value="VS Code",
        explicit=True,
    )
    r2 = mem.store(
        content="My favorite editor is Cursor",
        memory_type="preference",
        key="favorite editor",
        value="Cursor",
        explicit=True,
    )
    assert r2["action"] == "superseded"
    assert r2["supersedes"] == r1["memory_id"]

    found = mem.retrieve("what is my favorite editor?", top_k=5)
    active = _active(found)
    assert active, "Expected an active memory"
    assert "Cursor" in str(active[0].get("value") or active[0].get("content"))

    all_entries = [m for m in mem._memories if m.get("key") == "favorite editor"]
    active_for_key = [m for m in all_entries if m.get("active")]
    assert len(active_for_key) == 1, "Only one memory should be current"


# ---------------------------------------------------------------------------
# DEDUPLICATION
# ---------------------------------------------------------------------------

def test_repeated_save_is_idempotent(tmp_path):
    mem = UnifiedMemory(str(tmp_path))
    ids = []
    for _ in range(3):
        r = mem.store(
            content="My favorite language is Python",
            memory_type="preference",
            key="favorite language",
            value="Python",
            explicit=True,
        )
        assert r["success"] is True
        ids.append(r["memory_id"])

    assert len(set(ids)) == 1, "Identical saves must share one deterministic ID"
    assert len(mem._memories) == 1
    assert _active(mem._memories)


# ---------------------------------------------------------------------------
# EMPTY RETRIEVAL / HONEST FAILURES
# ---------------------------------------------------------------------------

def test_empty_retrieval_returns_nothing(tmp_path):
    mem = UnifiedMemory(str(tmp_path))
    mem.store(content="My favorite editor is VS Code", memory_type="preference")
    assert mem.retrieve("what is the weather in Berlin?") == []
    assert mem.search("what is the weather in Berlin?") is None


def test_empty_content_rejected(tmp_path):
    mem = UnifiedMemory(str(tmp_path))
    r = mem.store(content="   ")
    assert r["success"] is False
    assert r["stored"] is False


# ---------------------------------------------------------------------------
# INTENT EXTRACTION
# ---------------------------------------------------------------------------

def test_extract_remember_that():
    intent = extract_memory_intent("remember that my favorite language is Python")
    assert intent is not None
    assert intent["key"] == "favorite language"
    assert intent["value"] == "Python"
    assert intent["memory_type"] in ("preference", "fact")


def test_extract_remember_relationship():
    intent = extract_memory_intent("remember my brother's name is X")
    assert intent is not None
    assert intent["key"] == "brother's name"
    assert intent["value"] == "X"
    assert intent["memory_type"] == "relationship"


def test_extract_save_my_as():
    intent = extract_memory_intent("save my preference as dark mode")
    assert intent is not None
    assert intent["key"] == "preference"
    assert intent["value"] == "dark mode"
    assert intent["memory_type"] == "preference"


def test_extract_remember_clause():
    intent = extract_memory_intent("remember that I use VS Code for JARVIS")
    assert intent is not None
    assert intent["explicit"] is True
    assert "VS Code" in intent["content"]


def test_extract_dont_forget_event():
    intent = extract_memory_intent("don't forget my meeting at 3pm")
    assert intent is not None
    assert intent["memory_type"] == "event"


def test_extract_retrieval_query_is_none():
    assert extract_memory_intent("what is my sister's name?") is None
    assert extract_memory_intent("hello") is None


# ---------------------------------------------------------------------------
# LEGACY MIGRATION
# ---------------------------------------------------------------------------

def test_legacy_migration_idempotent(tmp_path):
    (tmp_path / "facts.json").write_text(
        json.dumps({"portfolio": "JARVIS AI OS"}), encoding="utf-8"
    )
    mem1 = UnifiedMemory(str(tmp_path))
    found = mem1.retrieve("what is your portfolio?", top_k=3)
    assert found, "Legacy fact must be migrated and searchable"
    assert "JARVIS" in str(found[0].get("value") or found[0].get("content"))

    mem2 = UnifiedMemory(str(tmp_path))
    facts = [m for m in mem2._memories if m.get("type") == "fact"]
    assert len(facts) == 1, "Migration must be idempotent (no duplicates)"


# ---------------------------------------------------------------------------
# FORMATTING
# ---------------------------------------------------------------------------

def test_format_memories_blocks(tmp_path):
    mem = UnifiedMemory(str(tmp_path))
    mem.store(
        content="My favorite editor is VS Code",
        memory_type="preference",
        key="favorite editor",
        value="VS Code",
        explicit=True,
    )
    found = mem.retrieve("favorite editor", top_k=1)
    block = mem.format_memories(found)
    assert "[MEMORY]" in block
    assert "[/MEMORY]" in block
    assert "Type: preference" in block
    assert "Key: favorite editor" in block
    assert "VS Code" in block
    assert "Confidence:" in block
    assert "Updated:" in block


# ---------------------------------------------------------------------------
# REGISTRY MEMORY TOOLS (LLM-accessible, canonical path)
# ---------------------------------------------------------------------------

def test_registry_memory_store_and_search(tmp_path, monkeypatch):
    monkeypatch.setattr(
        tr,
        "unified_memory",
        UnifiedMemory(str(tmp_path)),
    )
    store_result = tr.tool_registry.execute(
        "memory_store",
        content="My favorite editor is VS Code",
        memory_type="preference",
        key="favorite editor",
    )
    assert store_result["success"] is True
    assert store_result["verified"] is True
    assert store_result["metadata"]["memory_type"] == "preference"

    search_result = tr.tool_registry.execute(
        "memory_search",
        query="which editor do I prefer?",
    )
    assert search_result["success"] is True
    assert "VS Code" in search_result["output"]


def test_registry_memory_search_empty_is_honest(tmp_path, monkeypatch):
    monkeypatch.setattr(
        tr,
        "unified_memory",
        UnifiedMemory(str(tmp_path)),
    )
    result = tr.tool_registry.execute(
        "memory_search",
        query="the weather in Berlin",
    )
    assert result["success"] is False
    assert "no matching memory" in (result.get("error") or "").lower()


def test_llm_tool_call_memory_store_parses():
    calls = tool_call_parser.parse_text(
        '{"name": "memory_store", "arguments": '
        '{"content": "my project uses port 8000"}}'
    )
    assert calls and calls[0].name == "memory_store"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])