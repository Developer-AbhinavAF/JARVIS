"""Knowledge Engine Tests — Semantic knowledge system tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.knowledge_semantic import semantic_knowledge


def test_learn():
    result = semantic_knowledge.learn("Python is a high-level programming language", source_type="test")
    assert result["success"]
    print("  Knowledge Learn: PASS")
    return 1, 1


def test_retrieve():
    result = semantic_knowledge.retrieve("Python")
    assert "context" in result
    assert "sources" in result
    if result["context"]:
        assert "Python" in result["context"]
    print(f"  Knowledge Retrieve: context={len(result['context'])} chars")
    return 1, 1


def test_retrieve_empty():
    result = semantic_knowledge.retrieve("xyznonexistent12345")
    assert "context" in result
    print("  Knowledge Retrieve Empty: PASS")
    return 1, 1


def test_search():
    results = semantic_knowledge.search("Python", limit=5)
    assert isinstance(results, list)
    print(f"  Knowledge Search: {len(results)} results")
    return 1, 1


def test_multiple_learn():
    semantic_knowledge.learn("JARVIS is an AI assistant", source_type="test")
    semantic_knowledge.learn("The sky is blue", source_type="test")
    semantic_knowledge.learn("Water freezes at 0 degrees Celsius", source_type="test")
    result = semantic_knowledge.retrieve("sky blue")
    assert "context" in result
    print("  Knowledge Multiple Learn: PASS")
    return 1, 1


def test_stats():
    stats = semantic_knowledge.get_stats()
    assert "entries" in stats
    assert stats["entries"] > 0
    print(f"  Knowledge Stats: {stats['entries']} entries")
    return 1, 1


def test_learn_with_name():
    result = semantic_knowledge.learn("Test content with source name", source_type="manual", source_name="test_source")
    assert result["success"]
    print("  Knowledge Learn with Name: PASS")
    return 1, 1


def test_retrieve_with_source():
    result = semantic_knowledge.retrieve("test source")
    if result["sources"]:
        assert any(s.get("title") == "test_source" for s in result["sources"])
    print("  Knowledge Retrieve with Source: PASS")
    return 1, 1


def run():
    print("\n=== Knowledge Tests ===")
    total_passed = 0
    total = 0
    tests = [
        test_learn, test_retrieve, test_retrieve_empty, test_search,
        test_multiple_learn, test_stats, test_learn_with_name, test_retrieve_with_source,
    ]
    for t in tests:
        try:
            p, tot = t()
            total_passed += p
            total += tot
        except Exception as e:
            print(f"  {t.__name__}: FAIL ({e})")
            total += 1
    return total_passed, total


if __name__ == "__main__":
    run()
