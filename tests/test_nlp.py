"""QWEN3 Brain Tests — LLM-based intent classification, entities, context."""
import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.qwen3_brain import qwen3_brain, BrainResponse


async def test_intent_classification():
    """Test QWEN3 brain intent classification."""
    cases = [
        "hello",
        "open chrome", 
        "go to youtube",
        "search for python",
        "play music",
        "what is my name",
    ]
    
    for user_input in cases:
        try:
            response = await qwen3_brain.generate_complete(user_input)
            print(f"  {user_input}: {'PASS' if response.success else 'FAIL'}")
        except Exception as e:
            print(f"  {user_input}: FAIL ({e})")


async def test_tool_mapping():
    """Test QWEN3 brain tool selection."""
    cases = [
        "open chrome",
        "go to youtube", 
        "search for python",
        "get time",
        "system status",
    ]
    
    for user_input in cases:
        try:
            response = await qwen3_brain.generate_complete(user_input)
            print(f"  {user_input}: {'PASS' if response.success else 'FAIL'}")
        except Exception as e:
            print(f"  {user_input}: FAIL ({e})")


async def test_context_awareness():
    """Test context awareness."""
    # Test reference resolution
    from core.context_engine import context_engine
    
    context_engine.add_context("open youtube")
    context_engine.set_active_url("https://youtube.com")
    
    resolved = context_engine.resolve_reference("that")
    print(f"  Context resolution: {'PASS' if resolved else 'FAIL'}")


async def test_multilingual():
    """Test multi-language support."""
    cases = [
        "open chrome",
        "youtube kholo",
        "youtube khol do",
    ]
    
    for user_input in cases:
        try:
            response = await qwen3_brain.generate_complete(user_input)
            print(f"  {user_input}: {'PASS' if response.success else 'FAIL'}")
        except Exception as e:
            print(f"  {user_input}: FAIL ({e})")


async def main():
    print("=== QWEN3 Brain Tests ===")
    print("  Intent Classification:")
    await test_intent_classification()
    print("  Tool Mapping:")
    await test_tool_mapping()
    print("  Context Awareness:")
    await test_context_awareness()
    print("  Multi-language Support:")
    await test_multilingual()
    print("=== All Tests Complete ===")


if __name__ == "__main__":
    asyncio.run(main())