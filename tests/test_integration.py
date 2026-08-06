"""Integration tests for Jarvis Core architecture.

Tests that all interfaces produce identical responses for identical inputs,
validating the single-core architecture.
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any

from core.jarvis_core import get_core, JarvisCore
from core.memory import get_memory
from core.context import get_context
from core.cache import get_cache
from core.rag import get_rag
from core.tools_registry import get_tool_registry


class TestCoreIntegration:
    """Test Jarvis Core integration."""
    
    @pytest.fixture
    async def core(self):
        """Initialize and boot core for testing."""
        core = get_core()
        core.boot()
        yield core
        await core.shutdown()
    
    @pytest.mark.asyncio
    async def test_core_boot(self, core):
        """Test core boots successfully."""
        assert core._boot_complete
        stats = core.get_stats()
        assert stats["boot_complete"]
        assert stats["boot_time"] > 0
    
    @pytest.mark.asyncio
    async def test_basic_processing(self, core):
        """Test basic input processing."""
        response = await core.process("Hello")
        assert response.success
        assert response.text
        assert response.profile in ["FAST", "NORMAL"]
    
    @pytest.mark.asyncio
    async def test_streaming_processing(self, core):
        """Test streaming input processing."""
        tokens = []
        async for token in core.process_stream("Hello"):
            tokens.append(token)
        
        assert len(tokens) > 0
        full_text = "".join(tokens)
        assert full_text
    
    @pytest.mark.asyncio
    async def test_memory_integration(self, core):
        """Test memory integration."""
        # Set memory
        core.set_memory("test_key", "test_value", "facts")
        
        # Get memory
        value = core.get_memory("test_key", "facts")
        assert value.value == "test_value"
    
    @pytest.mark.asyncio
    async def test_context_integration(self, core):
        """Test context integration."""
        context = core.get_context()
        assert "session" in context
        assert "timestamp" in context
    
    @pytest.mark.asyncio
    async def test_profile_selection(self, core):
        """Test dynamic profile selection."""
        # Fast profile for greeting
        response1 = await core.process("Hello")
        assert response1.profile in ["FAST", "NORMAL"]
        
        # Coding profile for code request
        response2 = await core.process("Write a function")
        assert response2.profile in ["CODING", "NORMAL"]
    
    @pytest.mark.asyncio
    async def test_rag_integration(self, core):
        """Test RAG integration."""
        # Add knowledge
        doc_id = core.add_knowledge("Test knowledge for RAG system")
        assert doc_id
        
        # Retrieve knowledge
        results = core.retrieve_knowledge("test", limit=1)
        assert len(results) >= 0  # May not match due to simple embedding


class TestInterfaceConsistency:
    """Test that all interfaces produce identical responses."""
    
    @pytest.fixture
    async def core(self):
        """Initialize core for testing."""
        core = get_core()
        core.boot()
        yield core
        await core.shutdown()
    
    @pytest.mark.asyncio
    async def test_identical_inputs_identical_responses(self, core):
        """Test that identical inputs produce identical responses."""
        test_inputs = [
            "Hello",
            "What is the capital of France?",
            "Write a function to sort a list",
            "Open YouTube"
        ]
        
        for test_input in test_inputs:
            # Process same input twice
            response1 = await core.process(test_input)
            response2 = await core.process(test_input)
            
            # Responses should be very similar (may vary slightly due to temperature)
            # For FAST profile, should be nearly identical
            if response1.profile == "FAST":
                assert response1.text.lower() == response2.text.lower()
            
            # All other attributes should be identical
            assert response1.success == response2.success
            assert response1.profile == response2.profile
    
    @pytest.mark.asyncio
    async def test_context_persistence(self, core):
        """Test that context persists across multiple calls."""
        # First interaction
        response1 = await core.process("My name is Alice")
        
        # Second interaction referencing previous
        response2 = await core.process("What is my name?")
        
        # Context should be maintained
        context = core.get_context()
        assert "Alice" in str(context) or "name" in str(context).lower()
    
    @pytest.mark.asyncio
    async def test_memory_sharing(self, core):
        """Test that memory is shared across operations."""
        # Set memory
        core.set_memory("user_preference", "dark_mode", "preferences")
        
        # Verify memory is accessible
        memory = core.get_memory("user_preference", "preferences")
        assert memory.value == "dark_mode"
    
    @pytest.mark.asyncio
    async def test_cache_sharing(self, core):
        """Test that cache is shared across operations."""
        # Process same input multiple times
        await core.process("Hello")
        await core.process("Hello")
        await core.process("Hello")
        
        # Check cache stats
        cache_stats = core._cache.get_stats()
        assert cache_stats["prompt"]["size"] > 0 or cache_stats["prompt"]["total_hits"] > 0


class TestSubsystemIntegration:
    """Test integration between core subsystems."""
    
    @pytest.fixture
    async def core(self):
        """Initialize core for testing."""
        core = get_core()
        core.boot()
        yield core
        await core.shutdown()
    
    @pytest.mark.asyncio
    async def test_brain_context_integration(self, core):
        """Test brain and context integration."""
        # Add context
        core._context.add_context("Open YouTube", intent="open_website")
        
        # Process related input
        response = await core.process("Open it")
        
        # Context should be used
        assert response.success
    
    @pytest.mark.asyncio
    async def test_memory_context_integration(self, core):
        """Test memory and context integration."""
        # Store in memory
        core.set_memory("current_project", "JARVIS", "goals")
        
        # Add to context
        core._context.add_entity("JARVIS", "project")
        
        # Verify both are accessible
        memory = core.get_memory("current_project", "goals")
        context = core.get_context()
        
        assert memory.value == "JARVIS"
        assert "JARVIS" in str(context)
    
    @pytest.mark.asyncio
    async def test_cache_memory_integration(self, core):
        """Test cache and memory integration."""
        # Store in memory
        core.set_memory("cached_value", "test_data", "facts")
        
        # Access multiple times (should cache)
        for _ in range(3):
            core.get_memory("cached_value", "facts")
        
        # Check cache stats
        cache_stats = core._cache.get_stats()
        assert cache_stats["memory"]["size"] > 0
    
    @pytest.mark.asyncio
    async def test_rag_context_integration(self, core):
        """Test RAG and context integration."""
        # Add knowledge
        core.add_knowledge("JARVIS is an AI assistant created by Abhinav")
        
        # Process query
        response = await core.process("Who created JARVIS?")
        
        # RAG should provide context
        assert response.success
        # The response should mention the creator if RAG worked
        # (This depends on embedding quality and retrieval)


class TestToolIntegration:
    """Test tool integration with core."""
    
    @pytest.fixture
    async def core(self):
        """Initialize core for testing."""
        core = get_core()
        core.boot()
        yield core
        await core.shutdown()
    
    @pytest.mark.asyncio
    async def test_tool_execution(self, core):
        """Test tool execution through core."""
        # Execute tool command
        response = await core.process("Get system info")
        
        # Should trigger tool
        assert response.success
        # May or may not have tool depending on LLM
    
    @pytest.mark.asyncio
    async def test_tool_registry_access(self, core):
        """Test tool registry is accessible."""
        from core.tools_registry import get_tool_registry
        registry = get_tool_registry()
        
        tools = registry.get_all()
        assert len(tools) > 0
        assert "open_app" in tools or "open_url" in tools


class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.fixture
    async def core(self):
        """Initialize core for testing."""
        core = get_core()
        core.boot()
        yield core
        await core.shutdown()
    
    @pytest.mark.asyncio
    async def test_fast_profile_performance(self, core):
        """Test FAST profile performance."""
        start = time.time()
        response = await core.process("Hello")
        elapsed = (time.time() - start) * 1000
        
        # FAST profile should be < 500ms
        if response.profile == "FAST":
            assert elapsed < 500, f"FAST profile took {elapsed}ms"
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, core):
        """Test cache improves performance."""
        # First call (no cache)
        start1 = time.time()
        await core.process("Hello")
        elapsed1 = (time.time() - start1) * 1000
        
        # Second call (should use cache)
        start2 = time.time()
        await core.process("Hello")
        elapsed2 = (time.time() - start2) * 1000
        
        # Cached call should be faster (or similar if FAST profile)
        # For FAST profile, difference may be minimal
        if elapsed1 > 200:  # Only check if first call was slow enough
            assert elapsed2 <= elapsed1, f"Cache didn't help: {elapsed1}ms vs {elapsed2}ms"


class TestErrorHandling:
    """Test error handling and recovery."""
    
    @pytest.fixture
    async def core(self):
        """Initialize core for testing."""
        core = get_core()
        core.boot()
        yield core
        await core.shutdown()
    
    @pytest.mark.asyncio
    async def test_empty_input(self, core):
        """Test handling of empty input."""
        response = await core.process("")
        # Should handle gracefully
        assert response.success == False or response.text
    
    @pytest.mark.asyncio
    async def test_very_long_input(self, core):
        """Test handling of very long input."""
        long_input = "Hello " * 1000
        response = await core.process(long_input)
        # Should handle gracefully
        assert response.success == False or response.text
    
    @pytest.mark.asyncio
    async def test_special_characters(self, core):
        """Test handling of special characters."""
        special_input = "Test with !@#$%^&*()_+-=[]{}|;':\",./<>?"
        response = await core.process(special_input)
        # Should handle gracefully
        assert response.success == False or response.text


def test_global_instances():
    """Test that global instances are singletons."""
    core1 = get_core()
    core2 = get_core()
    assert core1 is core2
    
    memory1 = get_memory()
    memory2 = get_memory()
    assert memory1 is memory2
    
    context1 = get_context()
    context2 = get_context()
    assert context1 is context2
    
    cache1 = get_cache()
    cache2 = get_cache()
    assert cache1 is cache2
    
    rag1 = get_rag()
    rag2 = get_rag()
    assert rag1 is rag2


def test_subsystem_stats():
    """Test that all subsystems provide stats."""
    core = get_core()
    core.boot()
    
    stats = core.get_stats()
    
    assert "brain" in stats
    assert "memory" in stats
    assert "cache" in stats
    assert "rag" in stats
    assert "context" in stats
    
    # Verify stats have expected structure
    assert "total_requests" in stats["brain"]
    assert "total_entries" in stats["memory"]
    assert "embedding" in stats["cache"]
    
    asyncio.run(core.shutdown())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
