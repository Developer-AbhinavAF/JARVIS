"""Full pipeline integration test for JARVIS.

Tests the complete flow: user input → NLP → execution → memory → knowledge → LLM.
Requires: JARVIS boot (includes Ollama check, NLP init, execution engine).
"""
import asyncio
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app import JARVIS


class PipelineTestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def check(self, name: str, condition: bool, detail: str = ""):
        if condition:
            self.passed += 1
            print(f"  OK: {name}")
        else:
            self.failed += 1
            msg = f"  FAIL: {name}"
            if detail:
                msg += f" ({detail})"
            print(msg)
            self.errors.append(name)
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  Results: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print(f"  Failed: {', '.join(self.errors)}")
        print(f"{'='*60}")
        return self.failed == 0


async def test_intent_classification(jarvis, results):
    """Test NLP intent classification for various query types."""
    print("\n=== Intent Classification ===")
    
    test_cases = [
        # (query, expected_intent, description)
        ("open youtube", "OPEN_WEBSITE", "website open"),
        ("open chrome", "OPEN_APP", "app open"),
        ("search AI on github", "SEARCH_ON_PLATFORM", "platform search"),
        ("search python", "WEB_SEARCH", "web search"),
        ("weather in Mumbai", "GET_WEATHER", "weather"),
        ("what time is it", "DATETIME", "datetime"),
        ("tell me a joke", "JOKE", "joke"),
        ("take screenshot", "SCREENSHOT", "screenshot"),
        ("volume up", "VOLUME_CONTROL", "volume"),
        ("calculate 2 + 2", "CALCULATOR", "calculator"),
        ("set timer for 5 minutes", "TIMER", "timer"),
        ("hello", "GREETING", "greeting"),
        ("how are you", "CHAT", "chat"),
        ("what's up", "CHAT", "contraction chat"),
        ("who are you", "CHAT", "identity chat"),
        ("remember this important fact", "SAVE_MEMORY", "memory save imperative"),
        ("my name is test", "SAVE_MEMORY", "personal save"),
        ("what do you know about AI", "RECALL_MEMORY", "memory recall"),
        ("what is my name", "RECALL_MEMORY", "personal recall"),
        ("system status", "SYSTEM_STATUS", "system status"),
    ]
    
    for query, expected, desc in test_cases:
        output = jarvis._nlp.process(query)
        results.check(
            f"{desc}: '{query}' → {expected}",
            output.intent == expected,
            f"got {output.intent}"
        )


async def test_memory_operations(jarvis, results):
    """Test memory save and recall."""
    print("\n=== Memory Operations ===")
    
    # Save personal info
    r = await jarvis.handle("my name is pipeline_test_user")
    results.check(
        "Save name",
        r.get("success") and "pipeline_test_user" in r.get("response", ""),
        r.get("response", "")
    )
    
    r = await jarvis.handle("my email is test@pipeline.com")
    results.check(
        "Save email",
        r.get("success") and ("test@pipeline.com" in r.get("response", "") or r.get("intent") == "SAVE_MEMORY"),
        f"intent={r.get('intent')} response={r.get('response', '')[:60]}"
    )
    
    # Recall personal info
    r = await jarvis.handle("what is my name")
    results.check(
        "Recall name",
        r.get("success") and "pipeline_test_user" in r.get("response", ""),
        r.get("response", "")
    )
    
    r = await jarvis.handle("what is my email")
    resp = r.get("response", "")
    results.check(
        "Recall email",
        r.get("success") and ("test@pipeline.com" in resp or "email" in resp.lower()),
        resp[:80]
    )
    
    r = await jarvis.handle("what do you know about me")
    resp = r.get("response", "")
    results.check(
        "Recall all personal info",
        r.get("success") and "pipeline_test_user" in resp,
        resp[:80]
    )
    
    # Clean up
    jarvis._memory.save_preference("name", "", "personal")
    jarvis._memory.save_preference("email", "", "personal")


async def test_tool_execution(jarvis, results):
    """Test tool execution for various intents."""
    print("\n=== Tool Execution ===")
    
    # Greeting
    r = await jarvis.handle("hello")
    results.check("Greeting response", r.get("success"), r.get("response", ""))
    
    # Joke
    r = await jarvis.handle("tell me a joke")
    results.check("Joke response", r.get("success"), r.get("response", ""))
    
    # System status
    r = await jarvis.handle("system status")
    resp = r.get("response", "")
    results.check(
        "System status",
        r.get("success") and ("cpu" in resp.lower() or "memory" in resp.lower() or "system" in resp.lower()),
        resp[:100]
    )
    
    # Calculator
    r = await jarvis.handle("calculate 2 + 2")
    resp = r.get("response", "")
    results.check("Calculator", r.get("success"), resp[:80])
    
    # Datetime
    r = await jarvis.handle("what time is it")
    results.check("Datetime", r.get("success"), r.get("response", ""))


async def test_response_quality(jarvis, results):
    """Test that responses are meaningful (not empty or error)."""
    print("\n=== Response Quality ===")
    
    queries = [
        "hello",
        "how are you",
        "what's up",
        "tell me a joke",
        "who are you",
    ]
    
    for query in queries:
        r = await jarvis.handle(query)
        resp = r.get("response", "")
        results.check(
            f"Non-empty response for '{query}'",
            bool(resp) and len(resp) > 5,
            f"response={resp[:50]}"
        )


async def test_performance(jarvis, results):
    """Test response latency."""
    print("\n=== Performance ===")
    
    queries = ["hello", "what time is it", "system status"]
    latencies = []
    
    for query in queries:
        start = time.time()
        r = await jarvis.handle(query)
        elapsed = (time.time() - start) * 1000
        latencies.append(elapsed)
        results.check(
            f"Latency for '{query}' < 5000ms",
            elapsed < 5000,
            f"{elapsed:.0f}ms"
        )
    
    avg = sum(latencies) / len(latencies)
    results.check(f"Average latency < 3000ms", avg < 3000, f"{avg:.0f}ms")


async def main():
    print("=" * 60)
    print("  JARVIS Full Pipeline Integration Test")
    print("=" * 60)
    
    results = PipelineTestResults()
    
    # Boot JARVIS
    print("\nBooting JARVIS...")
    start = time.time()
    jarvis = JARVIS()
    await jarvis.boot()
    boot_time = time.time() - start
    print(f"Boot completed in {boot_time:.1f}s")
    
    # Run all test suites
    await test_intent_classification(jarvis, results)
    await test_memory_operations(jarvis, results)
    await test_tool_execution(jarvis, results)
    await test_response_quality(jarvis, results)
    await test_performance(jarvis, results)
    
    # Print summary
    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
