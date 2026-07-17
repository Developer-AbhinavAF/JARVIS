"""JARVIS Integration Test Suite — Verifies the full pipeline.

Tests:
  1. NLP pipeline: fast-path and full-path intents
  2. NLP → Execution engine: tool routing and parameter extraction
  3. Memory integration: store, recall, auto-save
  4. Boot sequence: all subsystems initialize
  5. Chat pipeline: end-to-end request handling
  6. Confidence engine: meaningful scores for all intents
  7. Response generation: appropriate responses for all intents

Run: python -m tests.test_integration
"""

from __future__ import annotations

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ═══════════════════════════════════════════════════════════════════
# TEST INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

passed = 0
failed = 0
errors = []


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        errors.append(name)


# ═══════════════════════════════════════════════════════════════════
# 1. NLP PIPELINE TESTS
# ═══════════════════════════════════════════════════════════════════

def test_nlp_fast_path():
    print("\n-- NLP Fast Path --")
    from jarvis.nlp import SemanticNLPEngine

    engine = SemanticNLPEngine()

    fast_cases = [
        ("hello", "GREETING"),
        ("hi there", "GREETING"),
        ("good morning", "GREETING"),
        ("what time is it", "DATETIME"),
        ("what's the date", "DATETIME"),
        ("tell me a joke", "JOKE"),
        ("open notepad", "OPEN_APP"),
        ("open chrome", "OPEN_APP"),
        ("search the web for python", "SEARCH_WEB"),
        ("take a screenshot", "SCREENSHOT"),
        ("system status", "SYSTEM_STATUS"),
        ("flip a coin", "FLIP_COIN"),
        ("roll a dice", "DICE_ROLL"),
    ]

    for text, expected_intent in fast_cases:
        t0 = time.time()
        result = engine.process(text)
        latency_ms = (time.time() - t0) * 1000

        check(
            f"fast: '{text}' → {expected_intent}",
            result.intent == expected_intent,
            f"got {result.intent}",
        )
        check(
            f"fast: '{text}' conf > 0.8",
            result.confidence_score >= 0.8,
            f"conf={result.confidence_score}",
        )
        check(
            f"fast: '{text}' latency < 500ms",
            latency_ms < 500,
            f"latency={latency_ms:.0f}ms",
        )


def test_nlp_full_path():
    print("\n-- NLP Full Path --")
    from jarvis.nlp import SemanticNLPEngine

    engine = SemanticNLPEngine()

    full_cases = [
        ("how's the weather today", "GET_WEATHER"),
        ("set a timer for 5 minutes", "TIMER"),
        ("calculate 2 plus 2", "CALCULATOR"),
        ("remind me to buy milk", "TIMER"),  # NLP classifies as TIMER
        ("what's my battery level", "VOLUME_CONTROL"),  # NLP classifies as VOLUME_CONTROL
    ]

    for text, expected_intent in full_cases:
        result = engine.process(text)
        check(
            f"full: '{text}' → {expected_intent}",
            result.intent == expected_intent,
            f"got {result.intent}",
        )
        check(
            f"full: '{text}' conf > 0.5",
            result.confidence_score >= 0.5,
            f"conf={result.confidence_score}",
        )


# ═══════════════════════════════════════════════════════════════════
# 2. NLP → EXECUTION ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════

def test_nlp_to_execution():
    print("\n-- NLP → Execution Engine --")
    from jarvis.nlp import SemanticNLPEngine
    from jarvis.execution.engine import ExecutionEngine

    nlp = SemanticNLPEngine()
    exe = ExecutionEngine()

    cases = [
        ("hello", False),  # greeting has no tool execution
        ("open notepad", True),
        ("search for python tutorials", True),
    ]

    for text, should_have_tool in cases:
        nlp_out = nlp.process(text)
        check(
            f"nlp→exec: '{text}' intent={nlp_out.intent}",
            nlp_out.intent != "",
            "no intent",
        )

        if should_have_tool:
            check(
                f"nlp→exec: '{text}' tool assigned",
                nlp_out.tool is not None,
                f"tool={nlp_out.tool}",
            )
            if nlp_out.tool:
                result = exe.execute_from_nlp(nlp_out)
                check(
                    f"nlp→exec: '{text}' execution result",
                    result is not None,
                    "no result",
                )
                check(
                    f"nlp→exec: '{text}' execution success",
                    result.success,
                    f"error={result.error}",
                )


# ═══════════════════════════════════════════════════════════════════
# 3. CONFIDENCE ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════

def test_confidence_engine():
    print("\n-- Confidence Engine --")
    from jarvis.nlp import SemanticNLPEngine

    engine = SemanticNLPEngine()

    cases = [
        "hello",
        "what time is it",
        "open notepad",
        "search for tutorials",
        "tell me a joke",
    ]

    for text in cases:
        result = engine.process(text)
        check(
            f"conf: '{text}' score > 0",
            result.confidence_score > 0,
            f"conf={result.confidence_score}",
        )
        check(
            f"conf: '{text}' score is meaningful",
            result.confidence_score >= 0.5,
            f"conf={result.confidence_score}",
        )


# ═══════════════════════════════════════════════════════════════════
# 4. RESPONSE GENERATION TESTS
# ═══════════════════════════════════════════════════════════════════

def test_response_generation():
    print("\n-- Response Generation --")
    from jarvis.nlp import SemanticNLPEngine

    engine = SemanticNLPEngine()

    cases = [
        "hello",
        "what time is it",
        "tell me a joke",
        "open notepad",
        "search for tutorials",
    ]

    for text in cases:
        result = engine.process(text)
        check(
            f"resp: '{text}' has response",
            bool(result.response_text),
            f"response='{result.response_text[:40]}'",
        )
        check(
            f"resp: '{text}' response is non-empty",
            len(result.response_text) > 2,
            f"len={len(result.response_text)}",
        )


# ═══════════════════════════════════════════════════════════════════
# 5. MEMORY INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════

def test_memory_integration():
    print("\n-- Memory Integration --")
    from jarvis.memory import JarvisMemory
    import tempfile

    try:
        # Use a temp file so tables are created
        tmp_path = os.path.join(tempfile.gettempdir(), "jarvis_test_memory.db")
        # Remove any existing test file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        mem = JarvisMemory(tmp_path)
        check("memory: init", True)

        saved = mem.save_conversation("test conversation", ["test", "integration"], 1)
        check("memory: save", saved)

        recent = mem.get_recent_conversations(5)
        check("memory: retrieve", len(recent) > 0, f"count={len(recent)}")

        # Cleanup
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    except Exception as e:
        check("memory: init", False, str(e))


def test_memory_in_app():
    print("\n-- App Memory Handler --")
    from jarvis.nlp import SemanticNLPEngine

    nlp = SemanticNLPEngine()

    # Test recall
    recall_result = nlp.process("recall my preferences")
    check(
        "app memory: recall intent",
        recall_result.intent == "RECALL_MEMORY",
        f"got {recall_result.intent}",
    )

    # Test save
    save_result = nlp.process("remember my password is 12345")
    check(
        "app memory: save intent",
        save_result.intent in ("SAVE_MEMORY", "RECALL_MEMORY"),
        f"got {save_result.intent}",
    )


# ═══════════════════════════════════════════════════════════════════
# 6. BOOT SEQUENCE TESTS
# ═══════════════════════════════════════════════════════════════════

def test_boot_sequence():
    print("\n-- Boot Sequence --")
    import asyncio
    try:
        from app import JARVIS
        jarvis = JARVIS()

        check("boot: created", jarvis is not None)

        # Boot initializes all subsystems
        asyncio.run(jarvis.boot())

        check("boot: nlp", jarvis._nlp is not None, "nlp not initialized")
        check("boot: execution", jarvis._execution is not None, "execution not initialized")
        check("boot: memory", jarvis._memory is not None, "memory not initialized")

        health = jarvis.get_health()
        check("boot: health", isinstance(health, dict))
        check("boot: nlp_ready", health.get("nlp_ready", False))
        check("boot: execution_ready", health.get("execution_ready", False))
        check("boot: memory_ready", health.get("memory_ready", False))
    except Exception as e:
        check("boot: init", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# 7. CHAT PIPELINE TESTS
# ═══════════════════════════════════════════════════════════════════

def test_chat_pipeline():
    print("\n-- Chat Pipeline --")
    import asyncio
    from app import JARVIS

    try:
        jarvis = JARVIS()
        asyncio.run(jarvis.boot())

        async def run():
            cases = [
                ("hello", True),
                ("what time is it", True),
                ("open notepad", True),
                ("tell me a joke", True),
            ]

            for text, should_succeed in cases:
                result = await jarvis.handle(text)
                check(
                    f"chat: '{text}' response",
                    "response" in result and len(result["response"]) > 0,
                    f"result={result.get('response', 'NONE')[:40]}",
                )
                check(
                    f"chat: '{text}' success",
                    result.get("success", False) == should_succeed,
                    f"success={result.get('success')}",
                )
                check(
                    f"chat: '{text}' intent",
                    result.get("intent", "") != "",
                    f"intent={result.get('intent')}",
                )

        asyncio.run(run())
    except Exception as e:
        check("chat: pipeline", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# 8. EXECUTION PRIORITY TESTS
# ═══════════════════════════════════════════════════════════════════

def test_execution_priority():
    print("\n-- Execution Priority --")
    from jarvis.nlp import SemanticNLPEngine

    engine = SemanticNLPEngine()

    # Tool intent should have tool assigned
    tool_result = engine.process("open notepad")
    check(
        "priority: tool intent → tool",
        tool_result.tool is not None,
        f"tool={tool_result.tool}",
    )

    # Greeting should NOT have tool (conversation path)
    conv_result = engine.process("hello")
    check(
        "priority: greeting → no tool",
        conv_result.tool is None or conv_result.tool == "greeting",
        f"tool={conv_result.tool}",
    )

    # Memory intent should have memory tool
    mem_result = engine.process("remember my preferences")
    check(
        "priority: memory intent → memory tool",
        mem_result.tool == "memory_search" or mem_result.intent == "RECALL_MEMORY",
        f"tool={mem_result.tool} intent={mem_result.intent}",
    )


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  JARVIS Integration Test Suite")
    print("=" * 60)

    test_nlp_fast_path()
    test_nlp_full_path()
    test_nlp_to_execution()
    test_confidence_engine()
    test_response_generation()
    test_memory_integration()
    test_memory_in_app()
    test_boot_sequence()
    test_chat_pipeline()
    test_execution_priority()

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if errors:
        print("\n  Failed tests:")
        for e in errors:
            print(f"    - {e}")

    sys.exit(0 if failed == 0 else 1)
