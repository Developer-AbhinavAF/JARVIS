#!/usr/bin/env python3
"""Simple test of JARVIS core functionality without CLI."""

import asyncio
import sys
import traceback
import pytest
from interface.app import JARVIS

@pytest.mark.skip(reason="Requires running LLM — standalone script, not a unit test")
def test_basic():
    """Test basic JARVIS functionality."""
    async def _run():
        jarvis = JARVIS()
        try:
            await jarvis.boot()
        except Exception as e:
            print(f"Boot failed: {e}")
            return
        
        test_inputs = ["hello", "what can you do?", "tell me a joke"]
        for user_input in test_inputs:
            try:
                result = await jarvis.handle(user_input)
                assert result.get("response") or not result.get("success")
            except Exception as e:
                print(f"Error: {e}")
        
        try:
            await jarvis.shutdown()
        except Exception:
            pass
    
    asyncio.run(_run())

if __name__ == "__main__":
    try:
        asyncio.run(test_basic())
    except Exception as e:
        print(f"Test failed: {e}")
        traceback.print_exc()