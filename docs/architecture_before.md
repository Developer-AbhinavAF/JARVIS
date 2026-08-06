# JARVIS Architecture Before Refactor

## Current State: Multiple Execution Paths

### Entry Points

1. **CLI Entry Point** (`main.py` → `interface/cli.py`)
   - Text Mode, Speech Mode, Debug Mode
   - Direct instantiation of `interface.app.JARVIS`
   - Own streaming logic
   - Own command parsing

2. **Desktop Interface** (`interface/desktop.py`)
   - System monitoring (CPU, RAM, GPU, battery, etc.)
   - Window tracking
   - Process monitoring
   - Independent monitoring logic

3. **Speech Interface** (`interface/speech.py`)
   - STT/TTS stub implementation
   - Separate speech engine
   - Not integrated with core

4. **Web/Desktop Backend** (`jarvis-desktop/backend/app.py`)
   - FastAPI server on port 8001
   - WebSocket support
   - System stats
   - Imports `interface.app.JARVIS` dynamically
   - Separate request handling

### Core Systems (Multiple Implementations)

#### 1. Multiple Application Classes

**`interface/app.JARVIS`** (Main application class)
- Own `_brain` (QWEN3 brain)
- Own `_execution_first` (execution runtime)
- Own `_router` (AI router)
- Own `_speech` (speech engine)
- Own `_desktop` (desktop monitor)
- Own boot sequence
- Own `handle()` method with fallback logic

**`jarvis-desktop/backend/app.py`** (FastAPI backend)
- Dynamically imports `interface.app.JARVIS`
- Own system stats collection
- Own WebSocket management
- Own action mapping
- Separate request/response handling

#### 2. Multiple Execution Engines

**`core/execution_first.py`** (Execution-first runtime)
- `SemanticIntentEngine` for command classification
- `ToolRegistry` with tool contracts
- `MemoryStore` for persistence
- `SessionContext` for context tracking
- `LocalNgramEmbeddings` for semantic similarity
- High-confidence command detection
- Intent-based routing

**`core/execution.py`** (Legacy execution engine - DEPRECATED)
- `ExecutionEngine` class
- `ExecutionTrace` for debugging
- Verification logic
- Memory integration
- Tool chain execution
- Planner integration

**`core/qwen3_brain.py`** (QWEN3 brain)
- `QWEN3Brain` class
- Thinking mode
- Streaming generation
- Context integration
- AI router usage
- Personality system

#### 3. Multiple Tool Registries

**`core/execution_first.ToolRegistry`** (New contract-based)
- ToolSpec with contracts
- Verification requirements
- Risk assessment
- Handler protocol
- Execute with verification

**`core/tools.ToolRegistry`** (Legacy)
- Simple registration
- Category-based
- Execute/verify functions
- No formal contracts
- Being replaced

#### 4. Multiple Memory Systems

**`core/execution_first.MemoryStore`** (New memory system)
- Facts, conversation, mistakes categories
- Embedding-based recall
- File persistence
- Knowledge directory
- Verified storage

**`core/context_engine.ContextEngine`** (Context tracking)
- Conversation history
- Entity tracking
- Reference resolution
- Context windows
- Recent history retrieval

**`data/conversation_history.json`** (File-based persistence)
- Simple JSON storage
- Used by some components
- No embedding support

#### 5. Multiple AI/LLM Paths

**`core/router.py`** (AI provider router)
- `OpenAICompatibleProvider` for API providers
- `OllamaProvider` for local models
- Priority-based routing
- Error handling
- Provider health tracking

**`core/qwen3_brain.py`** (QWEN3-specific)
- QWEN3:1.7B Q4_K_M via Ollama
- Thinking tokens
- Streaming responses
- Context integration
- Personality infusion

### Execution Path Analysis

#### CLI Path
```
User Input → CLI → interface.app.JARVIS.handle() → 
  ├─ qwen3_brain.think() (primary)
  ├─ execution_first.handle() (fallback for high-confidence)
  └─ qwen3_brain.generate_complete() (fallback)
```

#### Web/Desktop Path
```
User Input → FastAPI → jarvis-desktop/backend/app.py → 
  interface.app.JARVIS (dynamic import) → Same as CLI path
```

#### Speech Path
```
User Speech → interface/speech.py → (stub implementation)
```

### Problem Summary

1. **Duplicate Logic**: Same functionality implemented multiple times
2. **Inconsistent Responses**: Different paths may produce different results
3. **Maintenance Nightmare**: Changes must be propagated across multiple systems
4. **Memory Fragmentation**: Different memory systems not sharing data
5. **Tool Duplication**: Two tool registries with different contracts
6. **Context Inconsistency**: Context not shared across interfaces
7. **No Single Source of Truth**: Multiple "brains" making decisions
8. **Caching Issues**: No shared cache across components
9. **Profile Inconsistency**: Fixed parameters instead of dynamic profiles
10. **Testing Complexity**: Multiple paths to test for same functionality

### Component Dependencies

```
interface/cli.py
  └─ interface/app.py
      ├─ core/execution_first.py
      ├─ core/qwen3_brain.py
      │   └─ core/router.py
      ├─ core/context_engine.py
      ├─ interface/speech.py
      └─ interface/desktop.py

jarvis-desktop/backend/app.py
  └─ interface/app.py (dynamic import)
      └─ (same dependencies as CLI)

core/execution.py (DEPRECATED)
  ├─ core/tools.py
  ├─ core/planner_engine.py
  ├─ core/tool_chain_engine.py
  └─ core/context_engine.py
```

### Data Flow Issues

1. **Memory**: `execution_first.MemoryStore` vs `context_engine.ContextEngine` vs JSON files
2. **Context**: Not shared between CLI, Web, and Speech
3. **Tools**: Two registries with different tool definitions
4. **AI**: Router vs QWEN3 brain vs direct Ollama calls
5. **Knowledge**: Scattered across multiple systems

### Current Violations of Single Core Principle

- ❌ Separate NLP (intent engines in multiple places)
- ❌ Separate Memory (MemoryStore vs ContextEngine vs JSON)
- ❌ Separate Planner (planner_engine vs execution_first logic)
- ❌ Separate Context (SessionContext vs ContextEngine)
- ❌ Separate Speech (speech stub vs potential integration)
- ❌ Separate Tool Registry (two registries)
- ❌ Separate Router (implicit routing vs explicit router)
- ❌ Separate Execution Engine (execution_first vs execution.py)
- ❌ Separate RAG (embedding logic in multiple places)
- ❌ No unified caching strategy
