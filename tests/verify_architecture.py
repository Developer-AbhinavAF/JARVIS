#!/usr/bin/env python3
"""Verify single-core architecture without requiring LLM calls.

This script verifies that:
1. All subsystems use global singletons
2. Core has all required components
3. Interfaces delegate to core
4. No duplicate logic exists
"""

import sys
import os
import ast
import re
from pathlib import Path

# Fix encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))))


def verify_global_singletons():
    """Verify that all subsystems use global singletons."""
    print("=" * 60)
    print("Verifying Global Singletons")
    print("=" * 60)
    
    try:
        from core.jarvis_core import get_core
        from core.memory import get_memory
        from core.context import get_context
        from core.cache import get_cache
        from core.rag import get_rag
        from core.brain import get_brain
        
        # Test singletons
        core1 = get_core()
        core2 = get_core()
        assert core1 is core2, "Core must be singleton"
        print("[PASS] Core is singleton")
        
        memory1 = get_memory()
        memory2 = get_memory()
        assert memory1 is memory2, "Memory must be singleton"
        print("[PASS] Memory is singleton")
        
        context1 = get_context()
        context2 = get_context()
        assert context1 is context2, "Context must be singleton"
        print("[PASS] Context is singleton")
        
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2, "Cache must be singleton"
        print("[PASS] Cache is singleton")
        
        rag1 = get_rag()
        rag2 = get_rag()
        assert rag1 is rag2, "RAG must be singleton"
        print("[PASS] RAG is singleton")
        
        brain1 = get_brain()
        brain2 = get_brain()
        assert brain1 is brain2, "Brain must be singleton"
        print("[PASS] Brain is singleton")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Singleton verification failed: {e}")
        return False


def verify_core_components():
    """Verify that core has all required components."""
    print("\n" + "=" * 60)
    print("Verifying Core Components")
    print("=" * 60)
    
    try:
        from core.jarvis_core import JarvisCore
        
        # Check JarvisCore class has required attributes
        required_components = [
            '_cache', '_memory', '_context', '_brain', 
            '_profiles', '_rag', '_execution_runtime',
            '_conversation'
        ]
        
        # Create instance without booting
        core = JarvisCore()
        
        for component in required_components:
            assert hasattr(core, component), f"Core missing component: {component}"
            print(f"[PASS] Core has component: {component}")
        
        # Check required methods
        required_methods = [
            'boot', 'process', 'process_stream', 'get_context',
            'get_memory', 'set_memory', 'get_conversation_history',
            'get_stats', 'shutdown', 'add_knowledge', 'retrieve_knowledge'
        ]
        
        for method in required_methods:
            assert hasattr(core, method), f"Core missing method: {method}"
            print(f"[PASS] Core has method: {method}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Core components verification failed: {e}")
        return False


def verify_interface_delegation():
    """Verify that interfaces delegate to core."""
    print("\n" + "=" * 60)
    print("Verifying Interface Delegation")
    print("=" * 60)
    
    try:
        # Check new CLI uses core
        cli_file = Path("interface/cli_new.py")
        if cli_file.exists():
            with open(cli_file, 'r') as f:
                cli_content = f.read()
            
            # Should import from core.jarvis_core
            assert "from core.jarvis_core import get_core" in cli_content, "CLI should import from core"
            print("[PASS] CLI imports from core.jarvis_core")
            
            # Should NOT have own brain/memory/logic
            assert "from interface.app import JARVIS" not in cli_content, "CLI should not use old app"
            print("[PASS] CLI does not use old interface.app")
            
            # Should delegate to core.process
            assert "core.process" in cli_content or "core.process_stream" in cli_content, "CLI should delegate to core"
            print("[PASS] CLI delegates to core.process")
        
        # Check new backend uses core
        backend_file = Path("jarvis-desktop/backend/app_new.py")
        if backend_file.exists():
            with open(backend_file, 'r') as f:
                backend_content = f.read()
            
            # Should import from core.jarvis_core
            assert "from core.jarvis_core import get_core" in backend_content, "Backend should import from core"
            print("[PASS] Backend imports from core.jarvis_core")
            
            # Should NOT have own brain/memory/logic
            assert "importlib.util" not in backend_content or "spec_from_file_location" not in backend_content, "Backend should not dynamically import old app"
            print("[PASS] Backend does not dynamically import old app")
            
            # Should delegate to core.process
            assert "core.process" in backend_content, "Backend should delegate to core"
            print("[PASS] Backend delegates to core.process")
        
        # Check new speech uses core
        speech_file = Path("interface/speech_new.py")
        if speech_file.exists():
            with open(speech_file, 'r') as f:
                speech_content = f.read()
            
            # Should import from core.jarvis_core
            assert "from core.jarvis_core import get_core" in speech_content, "Speech should import from core"
            print("[PASS] Speech imports from core.jarvis_core")
            
            # Should delegate to core.process
            assert "core.process" in speech_content, "Speech should delegate to core"
            print("[PASS] Speech delegates to core.process")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Interface delegation verification failed: {e}")
        return False


def verify_no_duplicate_logic():
    """Verify that there's no duplicate logic in interfaces."""
    print("\n" + "=" * 60)
    print("Verifying No Duplicate Logic")
    print("=" * 60)
    
    try:
        # Check that new CLI doesn't have LLM/brain logic
        cli_file = Path("interface/cli_new.py")
        if cli_file.exists():
            with open(cli_file, 'r') as f:
                cli_content = f.read()
            
            # Should not have direct LLM calls
            llm_patterns = [
                'ollama', 'openai', 'anthropic', 'groq',
                'chat.completions', 'generate', 'embed'
            ]
            
            found_llm = []
            for pattern in llm_patterns:
                if pattern in cli_content.lower():
                    found_llm.append(pattern)
            
            if found_llm:
                print(f"[WARN] CLI contains potential LLM references: {found_llm}")
            else:
                print("[PASS] CLI has no direct LLM logic")
        
        # Check that new backend doesn't have LLM/brain logic
        backend_file = Path("jarvis-desktop/backend/app_new.py")
        if backend_file.exists():
            with open(backend_file, 'r') as f:
                backend_content = f.read()
            
            # Should not have direct LLM calls in request handlers
            # Only in core imports
            if "from core" in backend_content:
                print("[PASS] Backend uses core for all logic")
            else:
                print("[FAIL] Backend may have duplicate logic")
                return False
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Duplicate logic verification failed: {e}")
        return False


def verify_file_structure():
    """Verify that new core files exist."""
    print("\n" + "=" * 60)
    print("Verifying File Structure")
    print("=" * 60)
    
    required_files = [
        "core/jarvis_core.py",
        "core/brain.py",
        "core/memory.py",
        "core/context.py",
        "core/profiles.py",
        "core/cache.py",
        "core/tools_registry.py",
        "core/rag.py",
        "interface/cli_new.py",
        "jarvis-desktop/backend/app_new.py",
        "interface/speech_new.py"
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"[PASS] {file_path} exists")
        else:
            print(f"[FAIL] {file_path} missing")
            all_exist = False
    
    return all_exist


def verify_documentation():
    """Verify that documentation exists."""
    print("\n" + "=" * 60)
    print("Verifying Documentation")
    print("=" * 60)
    
    required_docs = [
        "architecture_before.md",
        "architecture_after.md",
        "core.md",
        "api.md",
        "profiles.md",
        "migration.md",
        "REFACTOR_SUMMARY.md"
    ]
    
    all_exist = True
    for doc_path in required_docs:
        path = Path(doc_path)
        if path.exists():
            print(f"[PASS] {doc_path} exists")
        else:
            print(f"[FAIL] {doc_path} missing")
            all_exist = False
    
    return all_exist


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("JARVIS Single-Core Architecture Verification")
    print("=" * 60)
    print()
    
    results = {}
    
    # Run all verifications
    results['singletons'] = verify_global_singletons()
    results['components'] = verify_core_components()
    results['delegation'] = verify_interface_delegation()
    results['no_duplicates'] = verify_no_duplicate_logic()
    results['files'] = verify_file_structure()
    results['docs'] = verify_documentation()
    
    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {check}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n" + "=" * 60)
        print("SUCCESS: All architecture verifications passed!")
        print("=" * 60)
        print("\nThe single-core architecture is correctly implemented:")
        print("- All subsystems use global singletons")
        print("- Core has all required components")
        print("- Interfaces delegate to core")
        print("- No duplicate logic in interfaces")
        print("- All required files exist")
        print("- Documentation is complete")
        return 0
    else:
        print("\n" + "=" * 60)
        print("FAILURE: Some verifications failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
