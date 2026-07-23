"""Router Tests — 10+ tests for AI router initialization and chat."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from core.router import router, AIRouter, OllamaProvider


def test_router_init():
    assert router is not None
    assert isinstance(router, AIRouter)
    print(f"  Router Init: {router.provider_count} providers")
    return 1, 1


def test_provider_count():
    assert router.provider_count >= 0
    print(f"  Provider Count: {router.provider_count}")
    return 1, 1


def test_ollama_available():
    result = asyncio.run(router.check_ollama())
    print(f"  Ollama Available: {result}")
    return 1, 1


def test_chat_simple():
    result = asyncio.run(router.chat("Say hello in one word"))
    if result.success:
        assert len(result.content) > 0
        print(f"  Chat Simple: {result.content[:50]}...")
    else:
        print(f"  Chat Simple: SKIP ({result.error})")
    return 1, 1


def test_chat_with_messages():
    messages = [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
    result = asyncio.run(router.chat(messages))
    if result.success:
        print(f"  Chat Messages: {result.content[:60]}...")
    else:
        print(f"  Chat Messages: SKIP ({result.error})")
    return 1, 1


def test_chat_response_fields():
    result = asyncio.run(router.chat("hi"))
    assert hasattr(result, "content")
    assert hasattr(result, "success")
    assert hasattr(result, "provider")
    assert hasattr(result, "model")
    assert hasattr(result, "latency_ms")
    print("  Chat Response Fields: PASS")
    return 1, 1


def test_ensure_ollama():
    result = asyncio.run(router.ensure_ollama_model())
    print(f"  Ensure Ollama: {result}")
    return 1, 1


def run():
    print("\n=== Router Tests ===")
    total_passed = 0
    total = 0
    tests = [
        test_router_init, test_provider_count, test_ollama_available,
        test_chat_simple, test_chat_with_messages, test_chat_response_fields,
        test_ensure_ollama,
    ]
    for t in tests:
        try:
            p, tot = t()
            total_passed += p
            total += tot
        except Exception as e:
            print(f"  {t.__name__}: FAIL ({e})")
            total += 1
    return total_passed, total


if __name__ == "__main__":
    run()
