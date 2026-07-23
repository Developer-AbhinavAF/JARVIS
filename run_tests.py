#!/usr/bin/env python3
"""Run all JARVIS tests and report results."""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

test_modules = [
    "tests.test_nlp",
    "tests.test_memory",
    "tests.test_tools",
    "tests.test_execution",
    "tests.test_desktop",
    "tests.test_knowledge",
    "tests.test_speech",
    "tests.test_vision",
    "tests.test_router",
    "tests.test_app",
]

total_passed = 0
total_tests = 0
start = time.time()

for module_name in test_modules:
    try:
        mod = __import__(module_name, fromlist=["run"])
        p, t = mod.run()
        total_passed += p
        total_tests += t
    except Exception as e:
        print(f"\n  FAILED to load {module_name}: {e}")

elapsed = time.time() - start
print(f"\n{'='*50}")
print(f"  RESULTS: {total_passed}/{total_tests} passed ({total_tests - total_passed} failed)")
print(f"  Time: {elapsed:.1f}s")
print(f"  Pass Rate: {total_passed/total_tests*100:.1f}%" if total_tests > 0 else "  No tests run")
print(f"{'='*50}")

if total_passed < total_tests:
    sys.exit(1)
