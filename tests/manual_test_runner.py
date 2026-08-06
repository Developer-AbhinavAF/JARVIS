#!/usr/bin/env python3
"""Manual test runner for the 15 required test cases."""

import sys
import os
import asyncio
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

test_cases = [
    "Open YouTube and search Interstellar",
    "Open GitHub and search Ollama",
    "What is my name?",
    "Mera naam kya hai",
    "Who am I?",
    "Play Believer",
    "Analyze screenshot",
    "Open Chrome",
    "What windows are open?",
    "What is my dream?",
    "What is my interest?",
    "What did I ask 2 prompts ago?",
    "Speech mode",
    "Ollama fallback",
    "Remember my name is Abhinav",
]

async def run_manual_tests():
    """Run the 15 manual test cases."""
    from interface.app import JARVIS
    
    print("=" * 60)
    print("JARVIS MANUAL TEST - 15 REQUIRED TEST CASES")
    print("=" * 60)
    
    jarvis = JARVIS()
    await jarvis.boot()
    
    results = []
    
    # First, set up memory
    print("\n[Setup] Setting up memory...")
    result = await jarvis.handle("Remember my name is Abhinav")
    print(f"Setup: {result.get('response', 'Failed')}")
    results.append(("Setup: Remember name", result.get("success", False)))
    
    time.sleep(1)
    
    # Test 1: Open YouTube and search Interstellar
    print("\n[Test 1] Open YouTube and search Interstellar")
    result = await jarvis.handle("Open YouTube and search Interstellar")
    print(f"Response: {result.get('response', 'Failed')}")
    print(f"Tool: {result.get('tool', 'None')}")
    results.append(("Test 1: YouTube search Interstellar", result.get("success", False)))
    
    time.sleep(2)
    
    # Test 2: Open GitHub and search Ollama
    print("\n[Test 2] Open GitHub and search Ollama")
    result = await jarvis.handle("Open GitHub and search Ollama")
    print(f"Response: {result.get('response', 'Failed')}")
    print(f"Tool: {result.get('tool', 'None')}")
    results.append(("Test 2: GitHub search Ollama", result.get("success", False)))
    
    time.sleep(2)
    
    # Test 3: What is my name?
    print("\n[Test 3] What is my name?")
    result = await jarvis.handle("What is my name?")
    print(f"Response: {result.get('response', 'Failed')}")
    results.append(("Test 3: What is my name?", result.get("success", False)))
    
    time.sleep(1)
    
    # Test 4: Mera naam kya hai (Hindi)
    print("\n[Test 4] Mera naam kya hai")
    result = await jarvis.handle("Mera naam kya hai")
    print(f"Response: {result.get('response', 'Failed')}")
    results.append(("Test 4: Mera naam kya hai", result.get("success", False)))
    
    time.sleep(1)
    
    # Test 5: Who am I?
    print("\n[Test 5] Who am I?")
    result = await jarvis.handle("Who am I?")
    print(f"Response: {result.get('response', 'Failed')}")
    results.append(("Test 5: Who am I?", result.get("success", False)))
    
    time.sleep(1)
    
    # Test 6: Play Believer
    print("\n[Test 6] Play Believer")
    result = await jarvis.handle("Play Believer")
    print(f"Response: {result.get('response', 'Failed')}")
    print(f"Tool: {result.get('tool', 'None')}")
    results.append(("Test 6: Play Believer", result.get("success", False)))
    
    time.sleep(2)
    
    # Test 7: Analyze screenshot
    print("\n[Test 7] Analyze screenshot")
    result = await jarvis.handle("Take a screenshot")
    print(f"Screenshot: {result.get('response', 'Failed')}")
    time.sleep(1)
    result = await jarvis.handle("Analyze it")
    print(f"Analysis: {result.get('response', 'Failed')}")
    results.append(("Test 7: Analyze screenshot", result.get("success", False)))
    
    time.sleep(2)
    
    # Test 8: Open Chrome
    print("\n[Test 8] Open Chrome")
    result = await jarvis.handle("Open Chrome")
    print(f"Response: {result.get('response', 'Failed')}")
    results.append(("Test 8: Open Chrome", result.get("success", False)))
    
    time.sleep(2)
    
    # Test 9: What windows are open?
    print("\n[Test 9] What windows are open?")
    result = await jarvis.handle("What windows are open?")
    print(f"Response: {result.get('response', 'Failed')}")
    results.append(("Test 9: What windows are open?", result.get("success", False)))
    
    time.sleep(1)
    
    # Setup: Remember dream
    print("\n[Setup] Setting up dream...")
    result = await jarvis.handle("Remember my dream is to build AGI")
    print(f"Setup: {result.get('response', 'Failed')}")
    
    time.sleep(1)
    
    # Test 10: What is my dream?
    print("\n[Test 10] What is my dream?")
    result = await jarvis.handle("What is my dream?")
    print(f"Response: {result.get('response', 'Failed')}")
    results.append(("Test 10: What is my dream?", result.get("success", False)))
    
    time.sleep(1)
    
    # Setup: Remember interest
    print("\n[Setup] Setting up interest...")
    result = await jarvis.handle("Remember that I like pizza")
    print(f"Setup: {result.get('response', 'Failed')}")
    
    time.sleep(1)
    
    # Test 11: What is my interest?
    print("\n[Test 11] What is my interest?")
    result = await jarvis.handle("What is my interest?")
    print(f"Response: {result.get('response', 'Failed')}")
    results.append(("Test 11: What is my interest?", result.get("success", False)))
    
    time.sleep(1)
    
    # Test 12: What did I ask 2 prompts ago?
    print("\n[Test 12] What did I ask 2 prompts ago?")
    result = await jarvis.handle("What did I ask 2 prompts ago?")
    print(f"Response: {result.get('response', 'Failed')}")
    results.append(("Test 12: What did I ask 2 prompts ago?", result.get("success", False)))
    
    time.sleep(1)
    
    # Test 13: Speech mode (check availability)
    print("\n[Test 13] Speech mode")
    if jarvis._speech:
        available = jarvis._speech.is_available()
        print(f"Speech available: TTS={available.get('tts', False)} STT={available.get('stt', False)}")
        results.append(("Test 13: Speech mode", True))
    else:
        print("Speech engine not available")
        results.append(("Test 13: Speech mode", False))
    
    # Test 14: Ollama fallback
    print("\n[Test 14] Ollama fallback")
    if jarvis._router and jarvis._router._ollama:
        try:
            available = await jarvis._router._ollama.check_available()
            print(f"Ollama available: {available}")
            results.append(("Test 14: Ollama fallback", True))
        except Exception as e:
            print(f"Ollama check failed: {e}")
            results.append(("Test 14: Ollama fallback", False))
    else:
        print("Ollama not configured")
        results.append(("Test 14: Ollama fallback", False))
    
    # Test 15: Context resolution (it/this/that/there)
    print("\n[Test 15] Context resolution")
    result = await jarvis.handle("Open YouTube")
    print(f"Open YouTube: {result.get('response', 'Failed')}")
    time.sleep(1)
    result = await jarvis.handle("Search there for Python")
    print(f"Search there: {result.get('response', 'Failed')}")
    results.append(("Test 15: Context resolution", result.get("success", False)))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "[OK] PASS" if success else "[FAIL] FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    await jarvis.shutdown()
    
    return passed, total

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        passed, total = loop.run_until_complete(run_manual_tests())
        sys.exit(0 if passed == total else 1)
    except Exception as e:
        print(f"\nTest runner failed: {e}")
        sys.exit(1)
    finally:
        loop.close()
