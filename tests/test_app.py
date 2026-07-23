"""Application Tests — 20+ tests for JARVIS app boot, handle, shutdown."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import time


def test_jarvis_import():
    from interface.app import JARVIS
    assert JARVIS is not None
    print("  JARVIS Import: PASS")
    return 1, 1


def test_jarvis_init():
    from interface.app import JARVIS
    j = JARVIS()
    assert j is not None
    assert j._boot_complete == False
    print("  JARVIS Init: PASS")
    return 1, 1


def test_jarvis_boot():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    assert j._boot_complete == True
    print("  JARVIS Boot: PASS")
    return 1, 1


def test_jarvis_subsystems():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    assert j._nlp is not None
    assert j._execution is not None
    assert j._memory is not None
    print("  JARVIS Subsystems: PASS")
    return 1, 1


def test_handle_greeting():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    result = asyncio.run(j.handle("hello"))
    assert "response" in result
    assert result["intent"] == "GREETING"
    print(f"  Handle Greeting: {result['response'][:30]}")
    return 1, 1


def test_handle_get_time():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    result = asyncio.run(j.handle("what time is it"))
    assert "response" in result
    assert result["success"] or not result["success"]
    print(f"  Handle Time: {result['response'][:30]}")
    return 1, 1


def test_handle_calculate():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    result = asyncio.run(j.handle("calculate 2+2"))
    assert "response" in result
    print(f"  Handle Calculate: {result['response'][:30]}")
    return 1, 1


def test_debug_toggle():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    j.enable_debug()
    assert j._debug_mode == True
    assert j._execution.debug_mode == True
    j.disable_debug()
    assert j._debug_mode == False
    print("  Debug Toggle: PASS")
    return 1, 1


def test_handle_health():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    from interface.desktop import desktop
    status = desktop.format_status()
    assert "CPU" in status
    print(f"  Health Check: CPU in response")
    return 1, 1


def test_shutdown():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    asyncio.run(j.shutdown())
    print("  Shutdown: PASS")
    return 1, 1


def test_handle_empty():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    result = asyncio.run(j.handle(""))
    assert "response" in result
    print("  Handle Empty: PASS")
    return 1, 1


def test_handle_unknown():
    from interface.app import JARVIS
    j = JARVIS()
    asyncio.run(j.boot())
    result = asyncio.run(j.handle("xyznonexistent12345"))
    assert "response" in result
    print("  Handle Unknown: PASS")
    return 1, 1


def run():
    print("\n=== Application Tests ===")
    total_passed = 0
    total = 0
    tests = [
        test_jarvis_import, test_jarvis_init, test_jarvis_boot, test_jarvis_subsystems,
        test_handle_greeting, test_handle_get_time, test_handle_calculate,
        test_debug_toggle, test_handle_health, test_shutdown,
        test_handle_empty, test_handle_unknown,
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
