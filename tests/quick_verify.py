#!/usr/bin/env python3
"""Quick verification of single-core architecture file structure."""

import sys
import os
from pathlib import Path

print("=" * 60)
print("JARVIS Single-Core Architecture Verification")
print("=" * 60)
print()

# Check required core files
core_files = [
    "core/jarvis_core.py",
    "core/brain.py", 
    "core/memory.py",
    "core/context.py",
    "core/profiles.py",
    "core/cache.py",
    "core/tools_registry.py",
    "core/rag.py"
]

print("Core Files:")
for file_path in core_files:
    path = Path(file_path)
    if path.exists():
        size = path.stat().st_size
        print(f"  [OK] {file_path} ({size} bytes)")
    else:
        print(f"  [MISSING] {file_path}")

print()

# Check new interface files
interface_files = [
    "interface/cli_new.py",
    "jarvis-desktop/backend/app_new.py", 
    "interface/speech_new.py"
]

print("New Interface Files:")
for file_path in interface_files:
    path = Path(file_path)
    if path.exists():
        size = path.stat().st_size
        print(f"  [OK] {file_path} ({size} bytes)")
    else:
        print(f"  [MISSING] {file_path}")

print()

# Check documentation
doc_files = [
    "architecture_before.md",
    "architecture_after.md",
    "core.md",
    "api.md",
    "profiles.md",
    "migration.md",
    "REFACTOR_SUMMARY.md"
]

print("Documentation Files:")
for file_path in doc_files:
    path = Path(file_path)
    if path.exists():
        size = path.stat().st_size
        print(f"  [OK] {file_path} ({size} bytes)")
    else:
        print(f"  [MISSING] {file_path}")

print()

# Check test files
test_files = [
    "tests/test_integration.py",
    "test_interface_consistency.py",
    "test_simple_consistency.py",
    "verify_architecture.py"
]

print("Test Files:")
for file_path in test_files:
    path = Path(file_path)
    if path.exists():
        size = path.stat().st_size
        print(f"  [OK] {file_path} ({size} bytes)")
    else:
        print(f"  [MISSING] {file_path}")

print()
print("=" * 60)
print("Verification Complete")
print("=" * 60)
