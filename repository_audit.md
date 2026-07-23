# Repository Audit Report

Generated: 2026-07-18

## Overview

| Metric | Value |
|--------|-------|
| Total files (with .venv + node_modules) | 74,266 |
| Python source files (jarvis/) | ~200 |
| Estimated total LOC (project code) | ~60,000+ |

## Duplicate Systems

### NLP Systems (54 files, ~18,671 LOC)
| Location | Files | LOC | Status |
|----------|-------|-----|--------|
| jarvis/nlp/ | 47 | ~17,542 | Primary semantic NLP engine |
| jarvis/ai_os/nlp/ | 2 | ~66 | AI Router-based NLP pipeline |
| jarvis/nlp_bridge.py | 1 | 68 | Bridge to old NLP pipeline |
| jarvis/nlp_pipeline.py | 1 | 203 | Fast multi-stage NLP pipeline |
| jarvis/intent_classifier.py | 1 | 256 | Intent classification |
| jarvis/intent_types.py | 1 | 270 | Intent type definitions |
| jarvis/entity_extractor.py | 1 | 266 | Entity extraction |

### Memory Systems (14 files, ~5,323 LOC)
| File | LOC | Type |
|------|-----|------|
| jarvis/memory.py | 1,029 | SQLite long-term memory |
| jarvis/memory_manager.py | 357 | ChromaDB learning memory |
| jarvis/memory_os.py | 477 | OS Memory with FTS5 + knowledge graph |
| jarvis/learning_memory.py | 441 | Self-learning memory |
| jarvis/nlp/memory_manager.py | 445 | In-memory NLP memory |
| jarvis/nlp/memory_bridge.py | 571 | NLP-to-memory bridge |
| jarvis/nlp/failure_memory.py | 194 | Tool failure tracking |
| jarvis/nlp/context_memory.py | 249 | Conversation context |
| jarvis/nlp/learning_engine.py | 674 | Preference learning |
| jarvis/learning/memory_optimizer.py | 125 | Memory dedup/compression |
| jarvis/learning/experience_db.py | 163 | Experience database |
| jarvis/knowledge/embeddings.py | 165 | Embedding engine |
| jarvis/tool_intelligence/tool_memory.py | 229 | Tool usage memory |
| jarvis/vision/screen_memory.py | 205 | Vision screen memory |

### Router Systems (42 files, ~8,691 LOC)
| Location | Files | LOC | Description |
|----------|-------|-----|-------------|
| jarvis/router/ | 21 | 4,831 | Primary AI Router |
| jarvis/ai_router/ | 14 | 2,239 | Duplicate AI Router |
| jarvis/router_service.py | 1 | 152 | Backward-compatible wrapper |
| jarvis/tool_router.py | 1 | 550 | Tool-first router |
| jarvis/action_router.py | 1 | 124 | Action router |
| jarvis/nlp/tool_router.py | 1 | 151 | NLP tool router |
| jarvis/nlp/knowledge_router.py | 1 | 249 | Knowledge router |
| jarvis/tool_intelligence/platform_router.py | 1 | 393 | Platform search router |
| jarvis/providers/openrouter.py | 1 | 2 | Re-export shim |

### Execution Systems (8+ files)
| File | LOC | Description |
|------|-----|-------------|
| jarvis/execution/engine.py | ~300 | Main execution engine |
| jarvis/execution/tool_registry.py | ~467 | Tool registry |
| jarvis/execution/core_tools.py | ~600 | Core tool implementations |
| jarvis/execution/verifier.py | ~150 | Tool result verification |
| jarvis/execution_engine.py | ~200 | Root execution engine |
| jarvis/command_engine.py | ~300 | Command processing |
| jarvis/tools.py | ~1,600 | Tool implementations |
| jarvis/tool_system.py | ~400 | Tool system |

## Dead Code / Stubs

| Pattern | Count | Files affected |
|---------|-------|----------------|
| `return None` | 160+ | ~55 files |
| `return []` | 57 | ~25 files |
| `return {}` | 9 | 9 files |
| `pass` (stub) | 66 | ~30 files |
| `raise NotImplementedError` | 8 | 2 files |
| `TODO` (code comments) | 4 | 4 files |
| `FIXME` | 0 | - |

## Unused Root-Level Files
- cli_speech.py
- cli_tests.py
- cli_ui.py
- import_check.py
- test.py, test_debug2.py, test_email.py, test_fixes.py, test_full_pipeline.py, test_memory_connect.py, test_remember.py
- architecture_audit.md, cli_migration_report.md
