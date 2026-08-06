"""Test unified backend architecture."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== Testing Unified Backend Architecture ===\n")

# Test 1: CLI uses JarvisCore
print("1. Testing CLI JarvisCore integration...")
try:
    from core.jarvis_core import JarvisCore
    core = JarvisCore()
    core.boot()
    print("[OK] CLI successfully uses JarvisCore")
except Exception as e:
    print(f"[FAIL] CLI JarvisCore integration failed: {e}")

# Test 2: API server exists
print("\n2. Testing API server availability...")
try:
    from interface.api import app
    print("[OK] Unified API server exists")
except Exception as e:
    print(f"[FAIL] API server import failed: {e}")

# Test 3: Desktop backend removed
print("\n3. Verifying duplicate desktop backend removed...")
desktop_backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jarvis-desktop", "backend")
if os.path.exists(desktop_backend_path):
    print(f"[FAIL] Duplicate desktop backend still exists at {desktop_backend_path}")
else:
    print("[OK] Duplicate desktop backend removed")

# Test 4: JarvisCore event system
print("\n4. Testing JarvisCore event system...")
try:
    from core.events import BaseEvent, ThinkingEvent, PlannerEvent, FinalResponse
    print("[OK] JarvisCore event system available")
except Exception as e:
    print(f"[FAIL] Event system import failed: {e}")

# Test 5: Speech engine integration
print("\n5. Testing speech engine integration...")
try:
    from interface.speech import speech_engine
    status = speech_engine.is_available()
    print(f"[OK] Speech engine available: {status}")
except Exception as e:
    print(f"[FAIL] Speech engine integration failed: {e}")

# Test 6: Tool registry integration
print("\n6. Testing tool registry integration...")
try:
    from core.tools_registry import tool_registry
    tools = tool_registry.search_candidates("youtube")
    print(f"[OK] Tool registry available with {len(tools)} tools found for 'youtube'")
except Exception as e:
    print(f"[FAIL] Tool registry integration failed: {e}")

# Test 7: Memory integration
print("\n7. Testing memory integration...")
try:
    from core.memory import unified_memory
    print("[OK] Unified memory available")
except Exception as e:
    print(f"[FAIL] Memory integration failed: {e}")

# Test 8: API endpoints
print("\n8. Testing API endpoints...")
try:
    from interface.api import app
    routes = [route.path for route in app.routes]
    print(f"[OK] API has {len(routes)} routes")
    expected_routes = ["/health", "/stats", "/logs", "/chat", "/ws"]
    for route in expected_routes:
        if any(route in r for r in routes):
            print(f"  - {route}: [OK]")
        else:
            print(f"  - {route}: [MISSING]")
except Exception as e:
    print(f"[FAIL] API endpoint check failed: {e}")

print("\n=== Unified Backend Test Complete ===")
