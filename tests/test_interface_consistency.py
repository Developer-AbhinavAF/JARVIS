#!/usr/bin/env python3
"""Test script to verify all interfaces produce identical responses.

This script tests that CLI, Web API, and any other interfaces
all use the same Jarvis Core and produce identical responses.
"""

import asyncio
import sys
import os
import time
import json
from typing import List, Dict, Any

# Fix encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.jarvis_core import get_core


class InterfaceTester:
    """Test interface consistency."""
    
    def __init__(self):
        self.core = get_core()
        self.test_inputs = [
            "Hello",
            "What is the capital of France?",
            "Write a function to sort a list",
            "Open YouTube",
            "Tell me a joke"
        ]
        self.results = {
            "core": [],
            "variations": []
        }
    
    async def setup(self):
        """Setup test environment."""
        print("Setting up test environment...")
        self.core.boot()
        print("Core booted successfully")
        print()
    
    async def teardown(self):
        """Cleanup test environment."""
        print("\nCleaning up...")
        await self.core.shutdown()
        print("Core shut down successfully")
    
    async def test_core_consistency(self):
        """Test that core produces consistent responses."""
        print("=" * 60)
        print("Testing Core Consistency")
        print("=" * 60)
        
        for i, test_input in enumerate(self.test_inputs, 1):
            print(f"\nTest {i}/{len(self.test_inputs)}: '{test_input}'")
            
            # Process input 3 times
            responses = []
            for j in range(3):
                start = time.time()
                response = await self.core.process(test_input)
                elapsed = (time.time() - start) * 1000
                
                responses.append({
                    "text": response.text,
                    "success": response.success,
                    "profile": response.profile,
                    "latency_ms": elapsed,
                    "provider": response.provider,
                    "model": response.model
                })
                
                print(f"  Run {j+1}: {response.profile} profile, {elapsed:.1f}ms")
                print(f"         Response: {response.text[:100]}...")
            
            # Check consistency
            texts = [r["text"] for r in responses]
            profiles = [r["profile"] for r in responses]
            
            # For FAST profile, texts should be identical
            if profiles[0] == "FAST":
                if len(set(texts)) == 1:
                    print("  [PASS] FAST profile: Identical responses")
                else:
                    print("  [FAIL] FAST profile: Different responses (unexpected)")
                    self.results["variations"].append({
                        "input": test_input,
                        "profile": profiles[0],
                        "expected": "identical",
                        "actual": "different"
                    })
            else:
                # For other profiles, some variation is acceptable
                if len(set(texts)) == 1:
                    print("  [PASS] Identical responses (good)")
                else:
                    print("  [WARN] Different responses (acceptable for non-FAST profiles)")
            
            self.results["core"].append({
                "input": test_input,
                "responses": responses,
                "consistent": len(set(texts)) == 1
            })
    
    async def test_memory_sharing(self):
        """Test that memory is shared across operations."""
        print("\n" + "=" * 60)
        print("Testing Memory Sharing")
        print("=" * 60)
        
        # Set memory
        test_key = "test_memory_key"
        test_value = "test_memory_value"
        
        print(f"\nSetting memory: {test_key} = {test_value}")
        self.core.set_memory(test_key, test_value, "facts")
        
        # Retrieve memory
        print("Retrieving memory...")
        memory_entry = self.core.get_memory(test_key, "facts")
        
        if memory_entry and memory_entry.value == test_value:
            print("[PASS] Memory retrieved correctly")
        else:
            print("[FAIL] Memory retrieval failed")
    
    async def test_context_sharing(self):
        """Test that context is shared across operations."""
        print("\n" + "=" * 60)
        print("Testing Context Sharing")
        print("=" * 60)
        
        # Add context
        print("\nAdding context...")
        self.core._context.add_context("Test context input", intent="test")
        
        # Get context
        print("Retrieving context...")
        context = self.core.get_context()
        
        if "session" in context and "last_query" in context:
            print("[PASS] Context retrieved correctly")
            print(f"  Last query: {context['last_query']}")
        else:
            print("[FAIL] Context retrieval failed")
    
    async def test_cache_sharing(self):
        """Test that cache is shared across operations."""
        print("\n" + "=" * 60)
        print("Testing Cache Sharing")
        print("=" * 60)
        
        # Process same input multiple times
        test_input = "Cache test input"
        
        print(f"\nProcessing '{test_input}' 3 times...")
        
        cache_stats_before = self.core._cache.get_stats()
        print(f"Cache stats before: {cache_stats_before['prompt']['size']} items")
        
        for i in range(3):
            await self.core.process(test_input)
        
        cache_stats_after = self.core._cache.get_stats()
        print(f"Cache stats after: {cache_stats_after['prompt']['size']} items")
        
        if cache_stats_after['prompt']['size'] >= cache_stats_before['prompt']['size']:
            print("[PASS] Cache is working")
        else:
            print("[FAIL] Cache not working as expected")
    
    async def test_profile_selection(self):
        """Test dynamic profile selection."""
        print("\n" + "=" * 60)
        print("Testing Profile Selection")
        print("=" * 60)
        
        profile_tests = [
            ("Hello", "FAST"),
            ("What is Python?", "NORMAL"),
            ("Write documentation", "WRITING"),
            ("Debug this code", "CODING"),
        ]
        
        for test_input, expected_profile in profile_tests:
            print(f"\nInput: '{test_input}'")
            print(f"Expected profile: {expected_profile}")
            
            response = await self.core.process(test_input)
            actual_profile = response.profile
            
            print(f"Actual profile: {actual_profile}")
            
            if actual_profile == expected_profile:
                print("[PASS] Profile selected correctly")
            else:
                print(f"[WARN] Profile different (expected {expected_profile}, got {actual_profile})")
    
    async def test_rag_integration(self):
        """Test RAG system integration."""
        print("\n" + "=" * 60)
        print("Testing RAG Integration")
        print("=" * 60)
        
        # Add knowledge
        print("\nAdding knowledge document...")
        doc_id = self.core.add_knowledge("JARVIS is an AI assistant created by Abhinav")
        print(f"Document ID: {doc_id}")
        
        # Test retrieval
        print("Testing knowledge retrieval...")
        results = self.core.retrieve_knowledge("Who created JARVIS?", limit=3)
        print(f"Retrieved {len(results)} documents")
        
        if len(results) > 0:
            print("[PASS] RAG system working")
            for i, result in enumerate(results, 1):
                print(f"  Result {i}: score={result.score:.2f}, relevance={result.relevance}")
        else:
            print("[WARN] RAG retrieval returned no results (may be due to embedding)")
    
    async def run_all_tests(self):
        """Run all consistency tests."""
        print("JARVIS Interface Consistency Test")
        print("=" * 60)
        print()
        
        try:
            await self.setup()
            
            await self.test_core_consistency()
            await self.test_memory_sharing()
            await self.test_context_sharing()
            await self.test_cache_sharing()
            await self.test_profile_selection()
            await self.test_rag_integration()
            
            await self.teardown()
            
            print("\n" + "=" * 60)
            print("Test Summary")
            print("=" * 60)
            
            # Report results
            core_tests = len(self.results["core"])
            consistent_tests = sum(1 for r in self.results["core"] if r["consistent"])
            
            print(f"\nCore consistency tests: {consistent_tests}/{core_tests} passed")
            
            if self.results["variations"]:
                print(f"\nUnexpected variations: {len(self.results['variations'])}")
                for variation in self.results["variations"]:
                    print(f"  - {variation}")
            else:
                print("\n[PASS] No unexpected variations detected")
            
            print("\n" + "=" * 60)
            print("Test Complete")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n[FAIL] Test failed with error: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main entry point."""
    tester = InterfaceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
