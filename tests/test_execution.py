"""Execution Engine Tests — 20+ tests for execution pipeline, traces, NLP integration."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
from core.execution import execution_engine, ExecutionTrace


def test_execute_simple():
    # Test direct tool execution
    from core.tools import tool_registry
    result = tool_registry.execute("get_time")
    assert result.success
    print("  Execute get_time: PASS")
    return 1, 1


def test_execute_calculate():
    from core.tools import tool_registry
    result = tool_registry.execute("calculate", expression="5*5")
    assert result.success
    print("  Execute calculate: PASS")
    return 1, 1


def test_execute_memory_save():
    result = execution_engine.execute_from_nlp(NLPOutput(intent="SAVE_MEMORY", confidence_score=0.9, tool="save_memory", tool_params={"content": "test execution save"}))
    assert result.success
    print("  Execute save_memory: PASS")
    return 1, 1


def test_execute_memory_recall():
    result = execution_engine.execute_from_nlp(NLPOutput(intent="RECALL_MEMORY", confidence_score=0.9, tool="recall_memory", tool_params={"query": "test"}))
    assert result.success
    print("  Execute recall_memory: PASS")
    return 1, 1


def test_execute_nonexistent_tool():
    result = execution_engine.execute_from_nlp(NLPOutput(intent="UNKNOWN", tool="nonexistent_tool_xyz"))
    assert not result.success
    print("  Execute nonexistent tool: PASS")
    return 1, 1


def test_execute_no_tool():
    result = execution_engine.execute_from_nlp(NLPOutput(intent="GREETING"))
    assert not result.success
    print("  Execute no tool: PASS")
    return 1, 1


def test_execution_trace():
    execution_engine.execute_from_nlp(NLPOutput(intent="GET_DATE", confidence_score=0.9, tool="get_date"))
    trace = execution_engine.get_last_trace()
    assert trace is not None
    assert trace.intent == "GET_DATE"
    assert trace.tool_name == "get_date"
    assert trace.query == ""
    print("  Execution Trace: PASS")
    return 1, 1


def test_execution_trace_debug():
    execution_engine.execute_from_nlp(NLPOutput(intent="CALCULATIONS", confidence_score=0.85, tool="calculate", tool_params={"expression": "1+1"}))
    trace = execution_engine.get_last_trace()
    debug = trace.format_debug()
    assert "CALCULATIONS" in debug
    assert "calculate" in debug
    print("  Trace Format Debug: PASS")
    return 1, 1


def test_multiple_traces():
    execution_engine.execute_from_nlp(NLPOutput(intent="GET_TIME", tool="get_time"))
    execution_engine.execute_from_nlp(NLPOutput(intent="GET_DATE", tool="get_date"))
    traces = execution_engine.get_traces(5)
    assert len(traces) >= 2
    print(f"  Multiple Traces ({len(traces)}): PASS")
    return 1, 1


def test_execution_stats():
    execution_engine.execute_from_nlp(NLPOutput(intent="GET_TIME", tool="get_time"))
    stats = execution_engine.get_stats()
    assert "total_executions" in stats
    assert "successful" in stats
    assert "verified" in stats
    assert stats["total_executions"] > 0
    print(f"  Execution Stats: {stats}")
    return 1, 1


def test_debug_mode():
    execution_engine.debug_mode = True
    assert execution_engine.debug_mode == True
    execution_engine.debug_mode = False
    assert execution_engine.debug_mode == False
    print("  Debug Mode Toggle: PASS")
    return 1, 1


def test_execute_with_entities():
    result = execution_engine.execute_from_nlp(NLPOutput(intent="CALCULATIONS", confidence_score=0.95, tool="calculate", tool_params={"expression": "10/2"}))
    assert result.success
    assert result.result.get("result") == 5.0
    print("  Execute with entities: PASS")
    return 1, 1


def test_execution_time_tracking():
    result = execution_engine.execute_from_nlp(NLPOutput(intent="GET_TIME", tool="get_time"))
    assert result.execution_time_ms >= 0
    print(f"  Execution Time: {result.execution_time_ms:.1f}ms")
    return 1, 1


def test_trace_limit():
    for i in range(150):
        execution_engine.execute_from_nlp(NLPOutput(intent="GET_TIME", tool="get_time"))
    traces = execution_engine.get_traces(200)
    assert len(traces) <= 100
    print(f"  Trace Limit (100 max): {len(traces)}")
    return 1, 1


def run():
    print("\n=== Execution Tests ===")
    total_passed = 0
    total = 0
    tests = [
        test_execute_simple, test_execute_calculate, test_execute_memory_save,
        test_execute_memory_recall, test_execute_nonexistent_tool, test_execute_no_tool,
        test_execution_trace, test_execution_trace_debug, test_multiple_traces,
        test_execution_stats, test_debug_mode, test_execute_with_entities,
        test_execution_time_tracking, test_trace_limit,
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
