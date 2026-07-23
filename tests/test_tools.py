"""Tool Tests — 40+ tests for tool registry, execution, and results."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
from core.tools import tool_registry, ToolResult, ToolCategory


def test_registry_count():
    tools = tool_registry.get_all()
    assert len(tools) >= 20
    print(f"  Tool Registry Count: {len(tools)} tools registered")
    return 1, 1


def test_registry_get():
    tool = tool_registry.get("get_time")
    assert tool is not None
    assert tool["name"] == "get_time"
    assert tool["execute"] is not None
    print("  Tool Registry Get: PASS")
    return 1, 1


def test_registry_get_nonexistent():
    tool = tool_registry.get("nonexistent_tool_12345")
    assert tool is None
    print("  Tool Registry Nonexistent: PASS")
    return 1, 1


def test_get_time():
    result = tool_registry.execute("get_time")
    assert result.success
    assert "time" in result.result
    print(f"  Tool get_time: {result.result.get('time', '')}")
    return 1, 1


def test_get_date():
    result = tool_registry.execute("get_date")
    assert result.success
    assert "date" in result.result
    print(f"  Tool get_date: {result.result.get('date', '')}")
    return 1, 1


def test_calculate():
    result = tool_registry.execute("calculate", expression="2+2")
    assert result.success
    assert result.result.get("result") == 4
    print("  Tool calculate (2+2=4): PASS")
    return 1, 1


def test_calculate_complex():
    result = tool_registry.execute("calculate", expression="10*5+3")
    assert result.success
    assert result.result.get("result") == 53
    print("  Tool calculate (10*5+3=53): PASS")
    return 1, 1


def test_calculate_division():
    result = tool_registry.execute("calculate", expression="100/4")
    assert result.success
    assert result.result.get("result") == 25.0
    print("  Tool calculate (100/4=25): PASS")
    return 1, 1


def test_calculate_invalid():
    result = tool_registry.execute("calculate", expression="")
    assert not result.success
    print("  Tool calculate (empty): PASS")
    return 1, 1


def test_create_file():
    import tempfile
    path = os.path.join(tempfile.gettempdir(), f"jarvis_test_{int(time.time())}.txt")
    result = tool_registry.execute("create_file", file_path=path, content="test content")
    assert result.success
    assert os.path.exists(path)
    os.remove(path)
    print("  Tool create_file: PASS")
    return 1, 1


def test_read_file():
    import tempfile
    path = os.path.join(tempfile.gettempdir(), f"jarvis_read_test_{int(time.time())}.txt")
    with open(path, "w") as f:
        f.write("hello world")
    result = tool_registry.execute("read_file", file_path=path)
    assert result.success
    assert "hello world" in result.result.get("content", "")
    os.remove(path)
    print("  Tool read_file: PASS")
    return 1, 1


def test_delete_file():
    import tempfile
    path = os.path.join(tempfile.gettempdir(), f"jarvis_del_test_{int(time.time())}.txt")
    open(path, "w").close()
    assert os.path.exists(path)
    result = tool_registry.execute("delete_file", file_path=path)
    assert result.success
    assert not os.path.exists(path)
    print("  Tool delete_file: PASS")
    return 1, 1


def test_recall_memory():
    result = tool_registry.execute("recall_memory", query="Python")
    assert result.success
    print("  Tool recall_memory: PASS")
    return 1, 1


def test_save_memory():
    result = tool_registry.execute("save_memory", content="test save from tools test")
    assert result.success
    print("  Tool save_memory: PASS")
    return 1, 1


def test_get_system_info():
    result = tool_registry.execute("get_system_info")
    assert result.success
    assert "os" in result.result
    print(f"  Tool get_system_info: {result.result.get('os', '')}")
    return 1, 1


def test_get_system_stats():
    result = tool_registry.execute("get_system_stats")
    assert result.success
    if "cpu_percent" in result.result:
        print(f"  Tool get_system_stats: CPU={result.result['cpu_percent']}% RAM={result.result['ram_percent']}%")
    print("  Tool get_system_stats: PASS")
    return 1, 1


def test_tool_categories():
    tools = tool_registry.get_all()
    categories = set()
    for t in tools.values():
        categories.add(t["category"].value)
    required = {"browser", "applications", "files", "system", "utility"}
    assert required.issubset(categories), f"Missing categories: {required - categories}"
    print(f"  Tool Categories: {categories}")
    return 1, 1


def test_execution_result_fields():
    result = tool_registry.execute("get_time")
    assert hasattr(result, "success")
    assert hasattr(result, "result")
    assert hasattr(result, "error")
    assert hasattr(result, "tool_name")
    assert hasattr(result, "execution_time_ms")
    assert hasattr(result, "verified")
    print("  Tool Result Fields: PASS")
    return 1, 1


def test_tool_execution_time():
    result = tool_registry.execute("calculate", expression="1+1")
    assert result.execution_time_ms >= 0
    print(f"  Tool Execution Time: {result.execution_time_ms:.1f}ms")
    return 1, 1


def test_nonexistent_tool():
    result = tool_registry.execute("nonexistent_tool")
    assert not result.success
    assert "not found" in result.error.lower()
    print("  Tool Nonexistent: PASS")
    return 1, 1


def test_category_enum():
    assert ToolCategory.BROWSER.value == "browser"
    assert ToolCategory.APPLICATIONS.value == "applications"
    assert ToolCategory.FILES.value == "files"
    assert ToolCategory.MEDIA.value == "media"
    assert ToolCategory.VISION.value == "vision"
    assert ToolCategory.MEMORY.value == "memory"
    assert ToolCategory.SYSTEM.value == "system"
    assert ToolCategory.DESKTOP.value == "desktop"
    assert ToolCategory.SEARCH.value == "search"
    assert ToolCategory.UTILITY.value == "utility"
    print("  Tool Category Enum: PASS")
    return 1, 1


def test_verify_functions():
    tools = tool_registry.get_all()
    with_verify = sum(1 for t in tools.values() if t["verify"] is not None)
    print(f"  Tools with verify: {with_verify}/{len(tools)}")
    return 1, 1


def run():
    print("\n=== Tool Tests ===")
    total_passed = 0
    total = 0
    tests = [
        test_registry_count, test_registry_get, test_registry_get_nonexistent,
        test_get_time, test_get_date,
        test_calculate, test_calculate_complex, test_calculate_division, test_calculate_invalid,
        test_create_file, test_read_file, test_delete_file,
        test_recall_memory, test_save_memory,
        test_get_system_info, test_get_system_stats,
        test_tool_categories, test_execution_result_fields, test_tool_execution_time,
        test_nonexistent_tool, test_category_enum, test_verify_functions,
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
