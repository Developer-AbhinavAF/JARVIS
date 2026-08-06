# JARVIS Core Documentation

## Overview

JARVIS Core is the single unified intelligence layer for all JARVIS interfaces. It is the ONLY source of truth for:

- NLP/LLM reasoning
- Memory storage and retrieval
- Context tracking
- Tool execution
- Profile selection
- Caching

All interfaces (CLI, Web, Speech) must use this core and ONLY this core.

## Architecture

```
JarvisCore
├── Brain (NLP/LLM reasoning)
├── Memory (unified memory system)
├── Context (unified context system)
├── Cache (shared cache system)
├── Profiles (dynamic profile system)
├── ToolRegistry (unified tool registry)
└── ExecutionRuntime (execution engine)
```

## Core Components

### 1. JarvisCore (`core/jarvis_core.py`)

The main entry point for all intelligence.

#### Methods

- `boot()` - Initialize all subsystems
- `process(user_input, context, profile_hint)` - Process input (non-streaming)
- `process_stream(user_input, context, profile_hint)` - Process input (streaming)
- `get_context()` - Get current context
- `get_memory(key, category)` - Get memory entry
- `set_memory(key, value, category)` - Set memory entry
- `get_conversation_history(limit)` - Get conversation history
- `get_stats()` - Get core statistics
- `shutdown()` - Shutdown core system

#### Usage

```python
from core.jarvis_core import get_core

# Get global core instance
core = get_core()

# Boot the core
core.boot()

# Process input
response = await core.process("Hello, JARVIS")
print(response.text)

# Process with streaming
async for token in core.process_stream("Tell me a joke"):
    print(token, end="")
```

### 2. Brain (`core/brain.py`)

Unified brain system with dynamic profile support.

#### Methods

- `think(user_input, context)` - Generate thinking tokens
- `generate(user_input, profile, context)` - Generate response (streaming)
- `generate_complete(user_input, profile, context)` - Generate response (non-streaming)
- `get_stats()` - Get brain statistics

#### Usage

```python
from core.brain import get_brain

brain = get_brain()

# Generate response
response = await brain.generate_complete("Hello")
print(response.content)

# Generate with streaming
async for token in brain.generate("Hello"):
    print(token, end="")
```

### 3. Memory (`core/memory.py`)

Unified memory system for all interfaces.

#### Methods

- `remember(key, value, category, embedding, metadata)` - Store memory
- `recall(key, category)` - Recall specific memory
- `recall_category(category)` - Recall all entries in category
- `forget(key, category)` - Remove memory entry
- `search(query, category, limit)` - Search memory
- `get_recent(category, limit)` - Get recent entries
- `get_stats()` - Get memory statistics

#### Categories

- `facts` - Factual information
- `preferences` - User preferences
- `goals` - User goals
- `mistakes` - Learned mistakes
- `conversation` - Conversation history
- `knowledge` - General knowledge

#### Usage

```python
from core.memory import get_memory

memory = get_memory()

# Remember something
memory.remember("name", "Alice", "facts")

# Recall something
entry = memory.recall("name", "facts")
print(entry.value)  # "Alice"

# Search
results = memory.search("Alice", limit=5)
```

### 4. Context (`core/context.py`)

Unified context system for all interfaces.

#### Methods

- `add_context(user_input, intent, tool, entities, metadata)` - Add context
- `resolve_reference(reference)` - Resolve pronoun references
- `get_context()` - Get current context
- `update_session(key, value)` - Update session context
- `set_active_app(app_name)` - Set active application
- `set_active_url(url)` - Set active URL
- `add_entity(name, entity_type, metadata)` - Add entity
- `get_recent_history(limit)` - Get recent conversation history
- `clear_context()` - Clear all context

#### Usage

```python
from core.context import get_context

context = get_context()

# Add context
context.add_context("Open YouTube", intent="open_website", tool="open_url")

# Resolve reference
result = context.resolve_reference("it")  # Returns last entity

# Get context
ctx = context.get_context()
print(ctx["session"]["current_app"])
```

### 5. Profiles (`core/profiles.py`)

Dynamic response profile system for adaptive generation.

#### Profile Types

- `FAST` - Greetings, simple questions, tool calling (think=False, temp=0.2, num_predict=128)
- `NORMAL` - Conversation, general questions (think=False, temp=0.5, num_predict=512)
- `WRITING` - Notes, essays, documentation (think=True, temp=0.7, num_predict=2048)
- `CODING` - Programming, debugging (think=True, temp=0.3, num_predict=4096)
- `PROJECT` - Large projects, websites (think=True, temp=0.5, num_predict=8192)

#### Methods

- `select_profile(input, context)` - Select best matching profile
- `get_profile(profile_type)` - Get specific profile
- `get_all_profiles()` - Get all available profiles

#### Usage

```python
from core.profiles import profile_manager, ProfileType

# Auto-select profile
profile = profile_manager.select_profile("Write a function")

# Get specific profile
profile = profile_manager.get_profile(ProfileType.CODING)

# Get LLM parameters
params = profile.get_llm_params()
print(params)  # {"temperature": 0.3, "num_predict": 4096, "think": True}
```

### 6. Cache (`core/cache.py`)

Shared cache system for all components.

#### Cache Types

- `embedding` - Text embeddings (2 hour TTL)
- `food` - Food data (24 hour TTL)
- `memory` - Memory entries (1 hour TTL)
- `conversation` - Conversation history (30 min TTL)
- `prompt` - Prompt responses (2 hour TTL)
- `tool` - Tool results (1 hour TTL)
- `context` - Context data (10 min TTL)

#### Methods

- `get(cache_type, key)` - Get from cache
- `set(cache_type, key, value, ttl)` - Set in cache
- `get_embedding(text)` - Get cached embedding
- `set_embedding(text, embedding)` - Cache embedding
- `get_memory(key)` - Get cached memory
- `set_memory(key, value, ttl)` - Cache memory
- `get_conversation(session_id)` - Get cached conversation
- `set_conversation(session_id, history)` - Cache conversation
- `get_prompt(prompt_hash)` - Get cached prompt response
- `set_prompt(prompt_hash, response)` - Cache prompt response
- `get_tool_result(tool_name, params_hash)` - Get cached tool result
- `set_tool_result(tool_name, params_hash, result)` - Cache tool result
- `get_context(context_key)` - Get cached context
- `set_context(context_key, value)` - Cache context
- `clear_cache(cache_type)` - Clear specific cache
- `get_stats()` - Get cache statistics

#### Usage

```python
from core.cache import get_cache

cache = get_cache()

# Cache and retrieve
cache.set("memory", "user:name", "Alice")
name = cache.get("memory", "user:name")  # "Alice"

# Cache embeddings
cache.set_embedding("hello world", [0.1, 0.2, 0.3])
embedding = cache.get_embedding("hello world")

# Get stats
stats = cache.get_stats()
print(stats)
```

### 7. ToolRegistry (`core/tools_registry.py`)

Unified tool registry with contracts and verification.

#### Methods

- `register(spec, handler)` - Register tool
- `get(name)` - Get tool specification
- `get_all()` - Get all tool specifications
- `get_by_category(category)` - Get tools by category
- `cards()` - Get tool cards for LLM
- `execute(name, **arguments)` - Execute tool

#### Tool Categories

- `BROWSER` - Browser operations
- `APPLICATIONS` - Application management
- `FILES` - File operations
- `MEDIA` - Media operations
- `VISION` - Vision operations
- `MEMORY` - Memory operations
- `SPEECH` - Speech operations
- `DESKTOP` - Desktop operations
- `SYSTEM` - System operations
- `SEARCH` - Search operations
- `UTILITY` - Utility operations

#### Usage

```python
from core.tools_registry import get_tool_registry, ToolSpec, ToolCategory, ToolRisk

registry = get_tool_registry()

# Get tool
spec = registry.get("open_app")
print(spec.description)

# Execute tool
result = registry.execute("open_app", app_name="chrome")
print(result.success)

# Get all tools
tools = registry.get_all()
for name, spec in tools.items():
    print(f"{name}: {spec.description}")
```

## Global Instances

All core subsystems have global instances that can be accessed via getter functions:

```python
from core.jarvis_core import get_core
from core.brain import get_brain
from core.memory import get_memory
from core.context import get_context
from core.cache import get_cache
from core.tools_registry import get_tool_registry
from core.profiles import profile_manager
```

## Response Format

All `process()` calls return a `CoreResponse`:

```python
@dataclass
class CoreResponse:
    text: str                    # Response text
    thinking: str                # Thinking tokens
    success: bool                # Success status
    tool: str                    # Tool used (if any)
    tool_result: ToolResult      # Tool execution result
    intent: str                  # Detected intent
    intent_confidence: float     # Intent confidence
    profile: str                 # Profile used
    provider: str                # AI provider used
    model: str                   # Model used
    latency_ms: float            # Latency in milliseconds
    context: Dict[str, Any]      # Current context
    error: str                   # Error message (if any)
```

## Integration Guide

### CLI Integration

```python
from core.jarvis_core import get_core

core = get_core()
core.boot()

# Main loop
while True:
    user_input = input("You: ")
    response = await core.process(user_input)
    print(f"Jarvis: {response.text}")
```

### Web API Integration

```python
from fastapi import FastAPI
from core.jarvis_core import get_core

app = FastAPI()
core = get_core()

@app.on_event("startup")
async def startup():
    core.boot()

@app.post("/process")
async def process(input: str):
    response = await core.process(input)
    return {"response": response.text}
```

### Speech Integration

```python
from core.jarvis_core import get_core

core = get_core()
core.boot()

# Main loop
while True:
    user_input = speech_to_text()
    response = await core.process(user_input)
    text_to_speech(response.text)
```

## Best Practices

1. **Always use global instances** - Use getter functions, don't create new instances
2. **Boot before use** - Always call `core.boot()` before processing
3. **Handle errors** - Check `response.success` and `response.error`
4. **Use streaming for long responses** - Use `process_stream()` for better UX
5. **Leverage caching** - Cache is automatic, but you can cache custom data
6. **Update context** - Call `context.add_context()` after each interaction
7. **Use profiles** - Let the system auto-select, or hint for specific profiles
8. **Verify tool results** - Check `tool_result.verified` before trusting results

## Migration Guide

### From Old System

**Old:**
```python
from interface.app import JARVIS
jarvis = JARVIS()
jarvis.boot()
response = await jarvis.handle(user_input)
```

**New:**
```python
from core.jarvis_core import get_core
core = get_core()
core.boot()
response = await core.process(user_input)
```

### From Multiple Systems

**Old (different systems for different interfaces):**
```python
# CLI uses interface.app.JARVIS
# Web uses jarvis-desktop/backend/app.py
# Speech uses interface.speech.py
```

**New (single core for all):**
```python
# All interfaces use core.jarvis_core.JarvisCore
from core.jarvis_core import get_core
core = get_core()
```

## Testing

```python
import pytest
from core.jarvis_core import get_core

@pytest.fixture
async def core():
    core = get_core()
    core.boot()
    yield core
    await core.shutdown()

async def test_process(core):
    response = await core.process("Hello")
    assert response.success
    assert "hello" in response.text.lower()
```

## Troubleshooting

### Core not booting

Check `core.get_stats()` for boot status and failures.

### Memory not persisting

Check that data directory exists and is writable.

### Context not resolving

Ensure you're calling `context.add_context()` after each interaction.

### Profiles not selecting correctly

Check profile keywords and patterns in `core/profiles.py`.

### Cache not working

Check cache statistics with `cache.get_stats()`.

## Performance

- Boot time: ~2-3 seconds
- Fast profile response: ~100-200ms
- Normal profile response: ~500-1000ms
- Writing profile response: ~1-2s
- Coding profile response: ~2-5s
- Project profile response: ~5-10s

## Security

- Tool execution requires verification
- High-risk tools require confirmation
- No code execution without verification
- Memory is persisted locally
- No external API calls without configuration
