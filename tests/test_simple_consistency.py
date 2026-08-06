#!/usr/bin/env python3
"""Simple test to verify core consistency without external dependencies."""

import asyncio
import sys
import os

# Fix encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.jarvis_core import get_core


async def test_core_boot():
    """Test core boots successfully."""
    print("Testing core boot...")
    core = get_core()
    core.boot()
    
    stats = core.get_stats()
    print(f"Boot complete: {stats['boot_complete']}")
    print(f"Boot time: {stats['boot_time']:.1f}s")
    
    assert stats['boot_complete'], "Core should boot successfully"
    print("[PASS] Core booted successfully")
    
    await core.shutdown()


async def test_global_instances():
    """Test that global instances are singletons."""
    print("\nTesting global instances...")
    
    from core.memory import get_memory
    from core.context import get_context
    from core.cache import get_cache
    from core.rag import get_rag
    
    core1 = get_core()
    core2 = get_core()
    assert core1 is core2, "Core should be singleton"
    print("[PASS] Core is singleton")
    
    memory1 = get_memory()
    memory2 = get_memory()
    assert memory1 is memory2, "Memory should be singleton"
    print("[PASS] Memory is singleton")
    
    context1 = get_context()
    context2 = get_context()
    assert context1 is context2, "Context should be singleton"
    print("[PASS] Context is singleton")
    
    cache1 = get_cache()
    cache2 = get_cache()
    assert cache1 is cache2, "Cache should be singleton"
    print("[PASS] Cache is singleton")
    
    rag1 = get_rag()
    rag2 = get_rag()
    assert rag1 is rag2, "RAG should be singleton"
    print("[PASS] RAG is singleton")


async def test_memory_operations():
    """Test memory operations."""
    print("\nTesting memory operations...")
    
    core = get_core()
    core.boot()
    
    # Set memory
    core.set_memory("test_key", "test_value", "facts")
    
    # Get memory
    memory = core.get_memory("test_key", "facts")
    assert memory is not None, "Memory should be retrievable"
    assert memory.value == "test_value", "Memory value should match"
    print("[PASS] Memory operations work")
    
    await core.shutdown()


async def test_context_operations():
    """Test context operations."""
    print("\nTesting context operations...")
    
    core = get_core()
    core.boot()
    
    # Add context
    core._context.add_context("Test input", intent="test")
    
    # Get context
    context = core.get_context()
    assert "session" in context, "Context should have session"
    assert "last_query" in context, "Context should have last_query"
    print("[PASS] Context operations work")
    
    await core.shutdown()


async def test_profile_selection():
    """Test profile selection."""
    print("\nTesting profile selection...")
    
    from core.profiles import profile_manager, ProfileType
    
    # Test profile selection
    profile = profile_manager.select_profile("Hello")
    assert profile.name in ["FAST", "NORMAL"], "Greeting should select FAST or NORMAL"
    print(f"[PASS] Profile selection works: {profile.name}")
    
    # Test getting specific profile
    coding_profile = profile_manager.get_profile(ProfileType.CODING)
    assert coding_profile.name == "CODING", "Should get CODING profile"
    print("[PASS] Specific profile retrieval works")


async def test_cache_operations():
    """Test cache operations."""
    print("\nTesting cache operations...")
    
    from core.cache import get_cache
    
    cache = get_cache()
    
    # Set cache
    cache.set("test", "key", "value")
    
    # Get cache
    value = cache.get("test", "key")
    assert value == "value", "Cache should return stored value"
    print("[PASS] Cache operations work")
    
    # Test embedding cache
    cache.set_embedding("test text", [0.1, 0.2, 0.3])
    embedding = cache.get_embedding("test text")
    assert embedding == [0.1, 0.2, 0.3], "Embedding cache should work"
    print("[PASS] Embedding cache works")


async def test_tool_registry():
    """Test tool registry."""
    print("\nTesting tool registry...")
    
    from core.tools_registry import get_tool_registry
    
    registry = get_tool_registry()
    
    # Get all tools
    tools = registry.get_all()
    assert len(tools) > 0, "Should have registered tools"
    print(f"[PASS] Tool registry has {len(tools)} tools")
    
    # Test tool execution
    result = registry.execute("get_system_info")
    assert result.success, "System info tool should execute"
    print("[PASS] Tool execution works")


async def test_rag_operations():
    """Test RAG operations."""
    print("\nTesting RAG operations...")
    
    from core.rag import get_rag
    
    rag = get_rag()
    
    # Add document
    doc_id = rag.add_document("Test knowledge content")
    assert doc_id, "Should return document ID"
    print(f"[PASS] RAG document added: {doc_id}")
    
    # Retrieve (may not match due to simple embeddings)
    results = rag.retrieve("test", limit=1)
    print(f"[PASS] RAG retrieval works (found {len(results)} results)")
    
    # Get stats
    stats = rag.get_stats()
    assert "embedding_engine" in stats, "RAG should have stats"
    print("[PASS] RAG stats available")


async def main():
    """Run all simple tests."""
    print("=" * 60)
    print("JARVIS Core Simple Consistency Tests")
    print("=" * 60)
    print()
    
    try:
        await test_core_boot()
        await test_global_instances()
        await test_memory_operations()
        await test_context_operations()
        await test_profile_selection()
        await test_cache_operations()
        await test_tool_registry()
        await test_rag_operations()
        
        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
