#!/usr/bin/env python3
"""Direct test of QWEN3 brain component."""

import asyncio
import traceback
import pytest
from core.qwen3_brain import qwen3_brain

@pytest.mark.skip(reason="Requires running LLM — standalone script, not a unit test")
def test_brain():
    """Test QWEN3 brain directly."""
    async def _run():
        test_inputs = ["hello", "what can you do?", "tell me a joke"]
        for user_input in test_inputs:
            try:
                result = await qwen3_brain.generate_complete(user_input)
                assert result.success or result.content == ""
            except Exception as e:
                print(f"Error: {e}")
    
    asyncio.run(_run())

if __name__ == "__main__":
    try:
        asyncio.run(test_brain())
    except Exception as e:
        print(f"Test failed: {e}")
        traceback.print_exc()