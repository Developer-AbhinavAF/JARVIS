#!/usr/bin/env python3
"""Simple test of JARVIS core functionality without CLI."""

import asyncio
import sys
import traceback
from interface.app import JARVIS

async def test_basic():
    """Test basic JARVIS functionality."""
    print("Initializing JARVIS...")
    jarvis = JARVIS()
    
    print("Booting JARVIS...")
    try:
        await jarvis.boot()
        print("Boot completed successfully")
    except Exception as e:
        print(f"Boot failed: {e}")
        traceback.print_exc()
        return
    
    print("DEBUG: Test about to start input testing")
    print(f"DEBUG: jarvis._brain = {jarvis._brain}")
    print(f"DEBUG: jarvis._execution = {jarvis._execution}")
    print("DEBUG: Test reached this point")
    
    print("\n" + "="*60)
    print("Testing basic input handling")
    print("="*60)
    
    test_inputs = [
        "hello",
        "what can you do?",
        "tell me a joke"
    ]
    
    for user_input in test_inputs:
        print(f"\nInput: {user_input}")
        try:
            result = await jarvis.handle(user_input)
            print(f"Response: {result.get('response', 'No response')}")
            print(f"Success: {result.get('success', False)}")
            print(f"Verified: {result.get('verified', False)}")
            print(f"Tool: {result.get('tool', 'none')}")
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("Test completed")
    print("="*60)
    
    print("Shutting down JARVIS...")
    try:
        await jarvis.shutdown()
    except Exception as e:
        print(f"Shutdown error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_basic())
    except Exception as e:
        print(f"Test failed: {e}")
        traceback.print_exc()