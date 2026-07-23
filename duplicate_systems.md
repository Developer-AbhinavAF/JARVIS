# Duplicate Systems Report

Generated: 2026-07-18

## 1. NLP Systems — 3 parallel implementations

### System A: jarvis/nlp/ (PRIMARY - 47 files, ~17,542 LOC)
Heavily modularized semantic NLP engine with:
- Intent classification (intent_classifier.py, intent_engine.py)
- Entity extraction (entity_extractor.py)
- Context tracking (context_engine.py, context_memory.py)
- Semantic parsing (semantic_engine.py, semantic_parser.py)
- Pattern matching (patterns.py)
- Parameter building (parameter_builder.py, parameter_parser.py)
- Confidence scoring (confidence.py, confidence_engine.py)
- Tool routing (tool_selector.py, tool_router.py, tool_registry.py)
- Learning (learning_engine.py, self_learning.py, self_improvement.py)
- Memory bridge (memory_bridge.py, memory_manager.py)
- Conversation analysis (conversation_analyzer.py)

### System B: jarvis/ai_os/nlp/ (2 files, ~66 LOC)
Thin NLP module that delegates to AI Router.

### System C: Root-level NLP files (5 files, ~1,063 LOC)
- nlp_bridge.py
- nlp_pipeline.py
- intent_classifier.py
- intent_types.py
- entity_extractor.py

**Recommendation:** Consolidate into single nlp.py

---

## 2. Memory Systems — 5+ parallel implementations

| System | File | LOC | Storage |
|--------|------|-----|---------|
| A | jarvis/memory.py | 1,029 | SQLite |
| B | jarvis/memory_manager.py | 357 | ChromaDB |
| C | jarvis/memory_os.py | 477 | SQLite + FTS5 |
| D | jarvis/learning_memory.py | 441 | SQLite |
| E | jarvis/nlp/memory_manager.py | 445 | In-memory |
| Bridge | jarvis/nlp/memory_bridge.py | 571 | NLP ↔ Memory |

**Recommendation:** Consolidate into single memory.py

---

## 3. Router Systems — 2 parallel AI router implementations

| Location | Files | LOC | Description |
|----------|-------|-----|-------------|
| jarvis/router/ | 21 | 4,831 | Primary AI Router |
| jarvis/ai_router/ | 14 | 2,239 | Duplicate AI Router |

Both have overlapping:
- capabilities.py
- config.py
- fallback.py
- health.py
- metrics.py
- models.py
- providers.py
- quota.py
- router.py
- streaming.py

**Recommendation:** Consolidate into single router.py

---

## 4. Execution Systems — Multiple

| System | Files | LOC |
|--------|-------|-----|
| jarvis/execution/ | 5 | ~1,500 |
| Root-level | execution_engine.py, command_engine.py, tools.py, tool_system.py | ~2,500 |

**Recommendation:** Consolidate into execution.py + tools.py

---

## 5. Tool Registries — 3+

- jarvis/execution/tool_registry.py
- jarvis/nlp/tool_registry.py
- jarvis/tool_router.py
- Root: tools.py, tool_system.py

**Recommendation:** Single tools.py
