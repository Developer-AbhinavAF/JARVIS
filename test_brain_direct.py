#!/usr/bin/env python3
"""Direct test of QWEN3 brain component."""

import asyncio
import traceback
from core.qwen3_brain import qwen3_brain

async def test_brain():
    """Test QWEN3 brain directly."""
    print("Testing QWEN3 brain directly...")
    
    test_inputs = [
        "hello",
        "what can you do?",
        "tell me a joke"
    ]
    
    for user_input in test_inputs:
        print(f"\nInput: {user_input}")
        try:
            result = await qwen3_brain.generate_complete(user_input)
            print(f"Success: {result.success}")
            print(f"Content: {result.content}")
            print(f"Provider: {result.provider}")
            print(f"Model: {result.model}")
            print(f"Latency: {result.latency_ms}ms")
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_brain())
    except Exception as e:
        print(f"Test failed: {e}")
        traceback.print_exc()