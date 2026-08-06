# JARVIS Architecture After Refactor

## New State: Single Core Engine

### Unified Architecture

```
                     JARVIS CORE
                        ↓
        ┌───────────────┼───────────────┐
        │               │               │
    Single Brain    Single Memory   Single Context
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
  Single Tool    Single Planner   Single Execution
    Registry         Engine         Engine
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
  Single Vision   Single Speech    Single RAG
    Engine          Engine          Engine
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
  Single Router  Dynamic Profiles  Shared Cache
    Engine          System            System
        │               │               │
        └───────────────┼───────────────┘
                        │
                        ↓
        ┌───────────────┼───────────────┐
        │               │               │
         CLI        Desktop UI      REST API
        │               │               │
        └───────────────┼───────────────┘
                        │
                SAME CORE INSTANCE
```

## Core Components

### 1. Jarvis Core (`core/jarvis_core.py`)

**Single entry point for all intelligence**

```python
class JarvisCore:
    """The single source of truth for all JARVIS intelligence."""
    
    def __init__(self):
        self.brain = Brain()           # Single NLP/LLM engine
        self.memory = Memory()         # Single memory system
        self.context = Context()       # Single context system
        self.planner = Planner()       # Single planning engine
        self.execution = Execution()   # Single execution engine
        self.tools = ToolRegistry()   # Single tool registry
        self.vision = Vision()         # Single vision engine
        self.speech = Speech()         # Single speech engine
        self.rag = RAG()               # Single RAG engine
        self.router = Router()         # Single AI router
        self.profiles = ProfileManager() # Dynamic profile system
        self.cache = Cache()           # Shared cache system
    
    async def process(self, input: str, context: dict = None) -> Response:
        """Unified processing endpoint for all interfaces."""
        # Dynamic profile selection
        profile = self.profiles.select_profile(input, context)
        
        # Single processing pipeline
        response = await self._pipeline(input, context, profile)
        
        return response
```

### 2. Unified Brain (`core/brain.py`)

**Single NLP/LLM reasoning engine**

```python
class Brain:
    """Unified brain using dynamic profiles."""
    
    def __init__(self, router: Router):
        self.router = router
        self.profiles = ProfileManager()
    
    async def think(self, input: str, profile: Profile) -> AsyncGenerator[str, None]:
        """Generate response using dynamic profile parameters."""
        params = profile.get_llm_params()
        
        # Use router with dynamic parameters
        async for token in self.router.generate(input, **params):
            yield token
```

### 3. Unified Memory (`core/memory.py`)

**Single memory system for all interfaces**

```python
class Memory:
    """Unified memory system."""
    
    def __init__(self, cache: Cache):
        self.cache = cache
        self.store = MemoryStore()
        self.embeddings = EmbeddingEngine()
    
    def remember(self, key: str, value: str, category: str) -> bool:
        """Store memory - shared across all interfaces."""
        # Single storage point
        pass
    
    def recall(self, query: str, limit: int = 5) -> list:
        """Retrieve memory - shared across all interfaces."""
        # Single retrieval point
        pass
```

### 4. Unified Context (`core/context.py`)

**Single context system for all interfaces**

```python
class Context:
    """Unified context system."""
    
    def __init__(self):
        self.state = SessionContext()
        self.entities = EntityManager()
        self.history = ConversationHistory()
    
    def update(self, key: str, value: str) -> None:
        """Update context - shared across all interfaces."""
        # Single context source
        pass
    
    def resolve(self, reference: str) -> str:
        """Resolve references - shared across all interfaces."""
        # Single resolution logic
        pass
```

### 5. Unified Tool Registry (`core/tools_registry.py`)

**Single tool registry with contracts**

```python
class ToolRegistry:
    """Unified tool registry."""
    
    def __init__(self):
        self.specs = {}  # ToolSpec contracts
        self.handlers = {}  # Tool handlers
    
    def register(self, spec: ToolSpec, handler: Handler) -> None:
        """Register tool - single registry for all interfaces."""
        pass
    
    def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute tool - single execution point."""
        pass
```

### 6. Dynamic Profile System (`core/profiles.py`)

**Adaptive generation based on input type**

```python
class ProfileManager:
    """Dynamic response profile selection."""
    
    PROFILES = {
        "fast": Profile(
            think=False,
            temperature=0.2,
            num_predict=128,
            use_cases=["greeting", "simple_question", "tool_calling"]
        ),
        "normal": Profile(
            think=False,
            temperature=0.5,
            num_predict=512,
            use_cases=["conversation", "general_question"]
        ),
        "writing": Profile(
            think=True,
            temperature=0.7,
            num_predict=2048,
            use_cases=["notes", "essay", "documentation", "explanation"]
        ),
        "coding": Profile(
            think=True,
            temperature=0.3,
            num_predict=4096,
            use_cases=["programming", "debugging", "architecture", "projects"]
        ),
        "project": Profile(
            think=True,
            temperature=0.5,
            num_predict=8192,
            use_cases=["large_project", "website", "jarvis_module"],
            file_by_file=True
        )
    }
    
    def select_profile(self, input: str, context: dict) -> Profile:
        """Automatically select appropriate profile."""
        # Analyze input and context
        # Return best matching profile
        pass
```

### 7. Shared Cache System (`core/cache.py`)

**Unified caching for all components**

```python
class Cache:
    """Shared cache system."""
    
    def __init__(self):
        self.embedding_cache = LRUCache(maxsize=1000)
        self.food_cache = LRUCache(maxsize=500)
        self.memory_cache = LRUCache(maxsize=2000)
        self.conversation_cache = LRUCache(maxsize=100)
        self.prompt_cache = LRUCache(maxsize=500)
    
    def get(self, cache_type: str, key: str) -> Any:
        """Get from cache - shared across all interfaces."""
        pass
    
    def set(self, cache_type: str, key: str, value: Any) -> None:
        """Set in cache - shared across all interfaces."""
        pass
```

## Interface Refactoring

### CLI (`interface/cli.py`)

**Becomes a thin interface layer**

```python
class CLI:
    """CLI interface - no logic, only I/O."""
    
    def __init__(self, core: JarvisCore):
        self.core = core  # Single core instance
    
    def run(self):
        """Main CLI loop."""
        while True:
            user_input = self.get_input()
            
            # Delegate ALL processing to core
            response = await self.core.process(user_input)
            
            # Display response
            self.display(response)
```

### Desktop/Web Backend (`jarvis-desktop/backend/app.py`)

**Becomes a thin API layer**

```python
class JarvisAPI:
    """FastAPI wrapper - no logic, only HTTP."""
    
    def __init__(self, core: JarvisCore):
        self.core = core  # Same core instance
    
    @app.post("/process")
    async def process(self, request: Request):
        """HTTP endpoint - delegates to core."""
        response = await self.core.process(request.input)
        return response
    
    @app.websocket("/ws")
    async def websocket(self, websocket: WebSocket):
        """WebSocket endpoint - delegates to core."""
        async for message in websocket:
            response = await self.core.process(message)
            await websocket.send_json(response)
```

### Speech (`interface/speech.py`)

**Becomes a thin I/O layer**

```python
class SpeechInterface:
    """Speech interface - no logic, only audio I/O."""
    
    def __init__(self, core: JarvisCore):
        self.core = core  # Same core instance
    
    def listen(self) -> str:
        """STT - convert speech to text."""
        pass
    
    def speak(self, text: str) -> None:
        """TTS - convert text to speech."""
        pass
    
    def run(self):
        """Main speech loop."""
        while True:
            user_input = self.listen()
            
            # Delegate ALL processing to core
            response = await self.core.process(user_input)
            
            # Speak response
            self.speak(response.text)
```

## Data Flow

### Unified Flow

```
User Input (any interface)
    ↓
Interface Layer (CLI/Web/Speech)
    ↓
JarvisCore.process()
    ↓
Profile Selection (dynamic)
    ↓
Context Update (shared)
    ↓
Memory Lookup (shared)
    ↓
Brain.think() (shared)
    ↓
Tool Execution (shared)
    ↓
Response Generation (shared)
    ↓
Memory Update (shared)
    ↓
Interface Layer (display/output)
    ↓
User Output
```

## Key Principles

### 1. Single Instance
- One `JarvisCore` instance
- One `Brain` instance
- One `Memory` instance
- One `Context` instance
- One `ToolRegistry` instance

### 2. Shared State
- Memory shared across CLI, Web, Speech
- Context shared across all interfaces
- Cache shared across all components
- Tools shared across all interfaces

### 3. Dynamic Adaptation
- Profile selection based on input
- Temperature/num_predict dynamic
- Think mode automatic
- No fixed parameters

### 4. Interface Separation
- CLI: Only I/O, no logic
- Web: Only HTTP, no logic
- Speech: Only audio, no logic
- All logic in Core

### 5. Verification
- All tools must verify
- Single verification logic
- Shared verification rules

## Migration Strategy

### Phase 1: Create Core
1. Create `core/jarvis_core.py`
2. Implement unified components
3. Migrate best implementations from existing code

### Phase 2: Refactor Interfaces
1. Refactor CLI to use Core
2. Refactor Web backend to use Core
3. Refactor Speech to use Core

### Phase 3: Cleanup
1. Remove duplicate implementations
2. Remove deprecated files
3. Update tests

### Phase 4: Verification
1. Test all interfaces produce identical responses
2. Test memory sharing
3. Test context sharing
4. Test profile selection

## Success Criteria

✅ **Single Implementation**
- One brain, one memory, one context, one tool registry
- No duplicate logic anywhere

✅ **Identical Responses**
- CLI, Web, Speech produce identical responses for same input
- All use same core instance

✅ **Shared State**
- Memory updates visible across all interfaces
- Context updates visible across all interfaces
- Cache shared across all components

✅ **Dynamic Profiles**
- Automatic profile selection
- Dynamic LLM parameters
- No fixed values

✅ **Interface Purity**
- CLI has no AI logic
- Web has no AI logic
- Speech has no AI logic
- All logic in Core

## File Structure After Refactor

```
core/
├── jarvis_core.py          # Single core entry point
├── brain.py                # Unified brain
├── memory.py               # Unified memory
├── context.py              # Unified context
├── tools_registry.py       # Unified tool registry
├── profiles.py             # Dynamic profile system
├── cache.py                # Shared cache system
├── router.py               # AI router (keep existing)
├── execution_first.py      # Keep as execution engine
└── vision.py               # Unified vision

interface/
├── cli.py                  # Thin CLI interface
├── desktop.py              # Desktop monitoring (keep)
└── speech.py               # Thin speech interface

jarvis-desktop/
└── backend/
    └── app.py              # Thin API interface

# Remove/deprecate:
# core/execution.py (legacy)
# core/qwen3_brain.py (migrate to brain.py)
# core/context_engine.py (migrate to context.py)
# core/tools.py (migrate to tools_registry.py)
# interface/app.py (replace with jarvis_core.py)
```
