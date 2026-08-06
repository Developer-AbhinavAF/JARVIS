"""Test new YouTube and Instagram tools."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools_registry import tool_registry

def test_tool_registration():
    """Test that new tools are properly registered."""
    print("=== Testing Tool Registration ===\n")

    # Test YouTube tools
    print("1. Checking YouTube video info tool...")
    results = tool_registry.search_candidates("youtube video info")
    assert len(results) > 0, "YouTube video info tool not found"
    print(f"[OK] Found: {results[0]['name']}")

    print("\n2. Checking YouTube download tool...")
    results = tool_registry.search_candidates("youtube download")
    assert len(results) > 0, "YouTube download tool not found"
    print(f"[OK] Found: {results[0]['name']}")

    print("\n3. Checking YouTube search tool...")
    results = tool_registry.search_candidates("youtube search")
    assert len(results) > 0, "YouTube search tool not found"
    print(f"[OK] Found: {results[0]['name']}")

    # Test Instagram tools
    print("\n4. Checking Instagram user info tool...")
    results = tool_registry.search_candidates("instagram user info")
    assert len(results) > 0, "Instagram user info tool not found"
    print(f"[OK] Found: {results[0]['name']}")

    print("\n5. Checking Instagram posts tool...")
    results = tool_registry.search_candidates("instagram posts")
    assert len(results) > 0, "Instagram posts tool not found"
    print(f"[OK] Found: {results[0]['name']}")

    print("\n=== All Tools Registered Successfully ===")

def test_tool_execution():
    """Test basic tool execution (without network calls)."""
    print("\n=== Testing Tool Execution ===\n")

    # Test with invalid arguments to see if tools are callable
    print("1. Testing YouTube video info with invalid URL...")
    result = tool_registry.execute("youtube_video_info", url="invalid_url")
    print(f"Result: {result.get('success', False)} (expected: False for invalid URL)")

    print("\n2. Testing Instagram user info with invalid username...")
    result = tool_registry.execute("instagram_user_info", username="invalid_username_12345")
    print(f"Result: {result.get('success', False)} (expected: False for invalid user)")

    print("\n=== Tool Execution Tests Complete ===")

if __name__ == "__main__":
    try:
        test_tool_registration()
        test_tool_execution()
        print("\n[SUCCESS] All tests passed!")
    except AssertionError as e:
        print(f"\n[FAILED] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
