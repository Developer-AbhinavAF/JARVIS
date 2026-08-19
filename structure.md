# JARVIS AI OS - Complete System Structure & Architecture

## Overview

JARVIS is a comprehensive AI Operating System built by Abhinav Yadav, featuring voice interaction, desktop automation, memory, and multiple interfaces (CLI, Web, Telephony). This document provides a complete structural overview for integration with external systems like n8n.

---

## System Ports & Services

### Primary Services

| Service | Port | Protocol | Purpose | Status |
|---------|------|----------|---------|--------|
| **Desktop Backend** | 8001 | HTTP/HTTPS/WSS | FastAPI server for Web UI | Active |
| **Telephony Server** | 8100 | HTTP/HTTPS/WSS | Twilio voice call integration | Active |
| **Frontend Dev** | 5173 | HTTP | Vite dev server (React) | Development |
| **Ollama LLM** | Variable | HTTP | Via ngrok tunnel | Active |

### External Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Ollama ngrok** | https://kiersten-nonpunishable-carry.ngrok-free.dev | Primary LLM access (jarvis-agi model) |
| **Twilio ngrok** | https://scolding-delusion-surreal.ngrok-free.dev | Public webhook for Twilio calls |
| **Groq API** | api.groq.com | Fallback LLM provider |
| **NASA API** | api.nasa.gov | Image search & APOD |

---

## Main Entry Points

### 1. CLI Interface
**File:** `main.py` → `interface/cli.py`

**Usage:**
```bash
python main.py              # Interactive menu
python main.py --text       # Text mode with streaming
python main.py --voice      # Speech mode
python main.py --api        # Start unified API server
python main.py --debug      # Debug mode
python main.py --health     # System health
python main.py "query"      # One-shot query
```

**Features:**
- Text-based interaction with Rich display
- Voice mode with speech recognition
- Real-time streaming responses
- Debug mode with detailed logging
- System health monitoring

### 2. Desktop Web Interface
**Backend:** `jarvis-desktop/backend/app.py` (FastAPI, Port 8001)
**Frontend:** `jarvis-desktop/frontend/src/App.tsx` (React, Port 5173)

**Startup:**
```bash
cd jarvis-desktop/backend
python app.py
```

**Features:**
- React-based web UI with cinematic loading
- Real-time chat with streaming
- System monitoring dashboard
- PC control panel
- Memory visualization
- Phone call interface
- Settings management

### 3. Telephony Interface
**File:** `interface/telephony/twilio_server.py` (Port 8100)

**Startup:**
```bash
python -m interface.telephony.twilio_server
```

**Features:**
- Twilio voice call integration
- Full-duplex audio streaming
- Speech-to-text (Twilio/Groq/Whisper/Deepgram)
- Text-to-speech (Edge-TTS)
- Call logging and transcription
- Web UI phone panel

---

## Core Architecture

### JarvisCore (Central Brain)
**File:** `core/jarvis_core.py`

**Responsibilities:**
- Central orchestrator for all interfaces
- Event-driven processing pipeline
- Memory and context management
- Tool execution coordination
- Multi-provider LLM routing

**Key Methods:**
- `boot()` - Initialize all subsystems
- `handle()` - Process user input (non-streaming)
- `process_stream()` - Process with streaming response
- `handle_with_image()` - Multimodal input processing

### Processing Pipeline

```
User Input
    ↓
WorldState Engine (context update)
    ↓
Planner Engine (intent classification)
    ↓
Prompt Assembler (build prompt with foods/memory/RAG)
    ↓
Brain Adapter (LLM communication)
    ↓
Thinking Middleware (parse thinking blocks)
    ↓
Tool Execution (if tools required)
    ↓
Verification (validate results)
    ↓
Response Generation
    ↓
Event Stream (to interface)
```

---

## LLM Provider System

### Primary: Ollama
**Model:** `jarvis-agi` (custom fine-tuned model)
**Access:** Via ngrok tunnel
**Configuration:** Environment variable `OLLAMA_HOST`

### Fallback: Groq
**Model:** `llama-3.1-8b-instant`
**API Key:** `GROQ_API_KEY` in `.env`
**Auto-switch:** When Ollama is unavailable

### Other Supported Providers
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- OpenRouter (multi-provider)
- LM Studio (local)

### Provider Router
**File:** `core/router.py` / `core/brain_adapter.py`

**Features:**
- Automatic provider selection
- Fallback chaining
- Capability-based routing
- Health monitoring

---

## Tool System

### Tool Registry
**File:** `core/tools_registry.py`

**Registered Tools:**
1. `open_application` - Launch desktop apps
2. `web_search` - Search the web
3. `youtube_video_info` - Get YouTube video details
4. `youtube_download` - Download YouTube videos
5. `youtube_search` - Search YouTube
6. `instagram_user_info` - Get Instagram user details
7. `instagram_posts` - Get Instagram posts
8. `get_system_status` - System resource monitoring
9. `code_fallback` - Code execution fallback

### Tool Execution
**File:** `core/execution_first.py`

**Features:**
- Semantic routing via intent patterns
- Safety layer for high-risk operations
- Verification of tool results
- 45-second timeout per tool
- Error handling and recovery

### Tool Call Parser
**File:** `core/toolcall_parser.py`

**Supports:**
- Native LLM tool calls (OpenAI format)
- JSON-in-text (various formats)
- Stringified arguments
- Legacy name(...) syntax
- Deduplication and validation

---

## Memory System

### 9-Tier Memory Architecture
**File:** `core/memory.py`

**Tiers:**
1. **Session Cache** - Current conversation context
2. **Facts** - User facts (name, preferences)
3. **Preferences** - User preferences and settings
4. **Goals** - Active goals and tasks
5. **Projects** - Project-related information
6. **Relationships** - People and connections
7. **Episodic** - Specific events and experiences
8. **Knowledge Graph** - Entity-relation triples
9. **Conversation Store** - Message history

### Storage
**Location:** `memory/` directory
**Format:** JSON files
**Files:**
- `facts.json`
- `preferences.json`
- `goals.json`
- `projects.json`
- `relationships.json`
- `episodic.json`
- `knowledge_graph.json`
- `mistakes.json`
- `patterns.json`

### Human Memory System
**File:** `core/memory_human.py`

**Features:**
- Active session tracking
- Important memory classification
- Daily summaries
- Index-based retrieval
- Sync capabilities

---

## RAG (Retrieval-Augmented Generation)

### RAG Engine
**File:** `core/rag.py`

**Method:** Keyword-based scoring (no embeddings)
**Sources:** `docs/`, `foods/`, `tool_docs/` markdown files
**Chunking:** ~1500 characters with ~150 char overlap
**Top-K:** 0-12 depending on intent

### Knowledge Sources
**Locations:**
- `docs/` - Technical documentation
- `foods/` - 22 prompt instruction files
- `tool_docs/` - Tool documentation
- `web_food/` - Web-specific instructions

---

## Foods System (Prompt Instructions)

### Dynamic Food Engine
**File:** `core/foods.py`

**Purpose:** Inject context-specific instructions into prompts

**Food Files:**
- `00_identity.md` - JARVIS identity
- `01_reasoning.md` - Reasoning guidelines
- `02_tools.md` - Tool usage
- `03_memory.md` - Memory handling
- `04_context.md` - Context resolution
- `05_desktop.md` - Desktop automation
- `06_browser.md` - Browser operations
- `07_speech.md` - Speech interaction
- `08_vision.md` - Vision capabilities
- `09_apps.md` - Application handling
- `10_personality.md` - Personality traits
- `11_safety.md` - Safety guidelines
- `12_examples.md` - Response examples
- `13_examples.md` - More examples
- `14_failure_recovery.md` - Error handling
- `15_security.md` - Security practices
- `16_best_practices.md` - Best practices
- `17_tool_aliases.md` - Tool aliases
- `18_planning.md` - Planning guidance
- `19_response_style.md` - Response formatting
- `20_music.md` - Music handling
- `21_desktop_ui.md` - Desktop UI context
- `22_nasa_visual.md` - NASA image integration

---

## Speech System

### Speech Engine
**File:** `speech/speech_engine.py`

### STT (Speech-to-Text) Chain
**File:** `speech/recognizer.py`

**Providers (cascading):**
1. faster-whisper (local, fast)
2. Groq Whisper (cloud)
3. Vosk (local, offline)
4. Google Web Speech API (fallback)

### TTS (Text-to-Speech)
**File:** `speech/edge_provider.py`

**Provider:** Edge-TTS (Microsoft)
**Features:**
- Disk caching
- Multiple voices
- Rate control
- High quality

### VAD (Voice Activity Detection)
**File:** `speech/vad.py`

**Methods (cascading):**
1. Silero (neural network)
2. WebRTC (energy-based)
3. Energy threshold (adaptive)

### Speech Pipeline
```
Microphone Input
    ↓
VAD (detect speech)
    ↓
Endpoint Detection (detect silence)
    ↓
STT (transcribe)
    ↓
Handler (process text)
    ↓
TTS (synthesize response)
    ↓
Playback (audio output)
```

---

## Vision System

### Vision Engine
**File:** `core/vision_engine.py`

**Capabilities:**
- Screenshot capture (pyautogui)
- OCR (pytesseract)
- Camera capture (OpenCV)
- Image upload support

**Status:** Partial implementation
- Object detection: Not implemented
- Scene understanding: Not implemented
- Face recognition: Not implemented

---

## API Endpoints

### Desktop Backend (Port 8001)

#### REST Endpoints
- `POST /api/chat` - Process chat message
- `GET /health` - Health check
- `GET /stats` - System statistics
- `GET /stats/core` - Core statistics
- `GET /context` - Get context
- `DELETE /context` - Clear context
- `GET /memory` - Memory statistics
- `GET /conversation` - Conversation history
- `GET /tools` - Available tools
- `GET /logs` - Recent logs
- `GET /api/system-stats` - System monitoring
- `GET /api/settings` - Get settings
- `POST /api/settings` - Update settings

#### WebSocket Endpoints
- `WS /ws` - Real-time communication
- `WS /ws/logs` - Log streaming
- `WS /ws/phone` - Phone panel updates

#### SSE Streaming
- `GET /process/stream` - Streamed response

### Telephony Server (Port 8100)

#### Endpoints
- `POST /voice` - Incoming call handler (TwiML)
- `POST /voice/events` - Twilio status events
- `POST /voice/status` - Call status updates
- `WS /voice/stream` - Twilio Media Stream
- `GET /voice/health` - Health check
- `WS /ws/phone` - Web UI phone panel

---

## Configuration

### Environment Variables (.env)

**LLM Providers:**
- `OLLAMA_HOST` - Ollama server URL
- `GROQ_API_KEY` - Groq API key
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `GOOGLE_API_KEY` - Google API key
- `OPENROUTER_API_KEY` - OpenRouter API key

**Twilio:**
- `TWILIO_ACCOUNT_SID` - Twilio account SID
- `TWILIO_AUTH_TOKEN` - Twilio auth token
- `TWILIO_PHONE_NUMBER` - Twilio phone number
- `TWILIO_WEBHOOK` - Public webhook URL

**NASA:**
- `NASA_API_KEY` - NASA API key

**System:**
- `JARVIS_HANDLE_TIMEOUT` - Handle timeout (default: 360s)
- `JARVIS_STREAM_TIMEOUT` - Stream timeout (default: 360s)
- `OLLAMA_WARMUP_TIMEOUT` - Ollama warmup timeout (default: 180s)

**Telephony:**
- `TELEPHONY_HOST` - Telephony server host (default: 0.0.0.0)
- `TELEPHONY_PORT` - Telephony server port (default: 8100)
- `WHISPER_PROVIDER` - STT provider (twilio/groq/whisper/deepgram)
- `JARVIS_SPEECH_TTS_VOICE` - TTS voice
- `JARVIS_SPEECH_TTS_RATE` - TTS rate

---

## Data Flow Examples

### Example 1: Simple Greeting (CLI)
```
User: "hello"
    ↓
CLI: main.py → interface/cli.py
    ↓
JarvisCore.handle("hello")
    ↓
Planner: CONVERSATION intent, FAST profile
    ↓
Brain Adapter: Ollama "jarvis-agi" model
    ↓
Response: "Hello Abhinav! How can I help you today?"
    ↓
CLI: Display response
```

### Example 2: Open Application (Web UI)
```
User: "open youtube" (Web UI)
    ↓
React: ChatPanel → handleSend()
    ↓
HTTP POST /api/chat
    ↓
FastAPI: get_jarvis() → jarvis.handle()
    ↓
Planner: EXTERNAL_ACTION intent, tools required
    ↓
Tool Registry: classify_input() → open_application
    ↓
Execution: os.system('start "" "youtube"')
    ↓
Verification: Check process running
    ↓
Response: "Launched youtube"
    ↓
FastAPI: JSON response with actions
    ↓
React: Display response + action
```

### Example 3: Phone Call (Telephony)
```
Incoming Call
    ↓
Twilio: POST /voice
    ↓
FastAPI: Return TwiML with WebSocket stream
    ↓
Twilio: Connect to WS /voice/stream
    ↓
Audio Stream: User speech
    ↓
STT: Transcribe speech
    ↓
JarvisCore.handle(transcribed_text)
    ↓
Planner → Brain → Response
    ↓
TTS: Synthesize response
    ↓
Audio Stream: Send back to Twilio
    ↓
Twilio: Play audio to caller
```

### Example 4: Web Search with n8n Integration
```
n8n: HTTP POST /api/chat
    ↓
Body: {"message": "search for python tutorials"}
    ↓
FastAPI: Process request
    ↓
JarvisCore.handle()
    ↓
Planner: WEB_SEARCH intent
    ↓
Tool Registry: web_search tool
    ↓
Execution: Perform web search
    ↓
Response: Search results
    ↓
FastAPI: JSON response
    ↓
n8n: Process results
```

---

## Performance Characteristics

### Processing Times
- Health check: <10ms
- System stats: <50ms
- Simple conversation (FAST): 100-200ms
- Normal response: 500-1000ms
- Writing task: 1-2s
- Coding task: 2-5s
- Complex reasoning: 5-10s

### Resource Usage
- Idle: ~200MB RAM
- Active conversation: ~300-500MB RAM
- With Ollama: Depends on model size
- With vision features: +100-200MB RAM

### Concurrency
- Multiple CLI sessions: Supported
- Multiple web clients: Supported (singleton JARVIS)
- Concurrent phone calls: Supported (CallManager)
- Tool execution: 45s timeout per tool

---

## Integration Points for n8n

### 1. Chat Interface
**Endpoint:** `POST http://localhost:8001/api/chat`

**Request:**
```json
{
  "message": "Your message here",
  "session_id": "optional-session-id",
  "stream": false
}
```

**Response:**
```json
{
  "response": "JARVIS response",
  "session_id": "default",
  "timestamp": "2024-01-15T10:30:00.123",
  "actions": [...],
  "intent": "greeting",
  "intent_confidence": 0.95,
  "tool": "",
  "verified": false,
  "total_ms": 150.5
}
```

### 2. System Monitoring
**Endpoint:** `GET http://localhost:8001/api/system-stats`

**Response:**
```json
{
  "cpu": {"usage": 25.5, "cores": 8},
  "memory": {"used": 8.2, "total": 16.0, "percentage": 51.2},
  "battery": {"percentage": 85, "isCharging": true},
  "disk": {"used": 250.5, "total": 500.0, "percentage": 50.1},
  "network": {"downloadSpeed": 1024000, "uploadSpeed": 512000, "ping": 15.5},
  "processes": {"count": 145}
}
```

### 3. Memory Access
**Endpoint:** `GET http://localhost:8001/memory`

**Response:**
```json
{
  "total_entries": 25,
  "categories": {
    "facts": 10,
    "preferences": 5,
    "goals": 3,
    "mistakes": 2,
    "conversation": 5
  }
}
```

### 4. Tool Execution
**Endpoint:** `POST http://localhost:8001/api/chat`

**Tool Execution via Chat:**
```json
{
  "message": "open notepad"
}
```

**Direct Tool Call (via tool registry):**
Available through internal tool_registry.execute()

### 5. Context Management
**Endpoint:** `GET http://localhost:8001/context`

**Response:**
```json
{
  "session": {
    "current_app": "chrome",
    "current_website": "https://github.com",
    "last_tool": "read_file",
    "last_user_request": "Read the README"
  },
  "last_query": "Read the README",
  "last_intent": "read_file",
  "timestamp": 1698765432.123
}
```

### 6. WebSocket Integration
**Endpoint:** `WS ws://localhost:8001/ws`

**Message:**
```json
{
  "input": "Your message",
  "context": {},
  "profile_hint": "NORMAL"
}
```

**Response:**
```json
{
  "text": "Response",
  "success": true,
  "tool": null,
  "intent": "greeting",
  "intent_confidence": 0.95
}
```

---

## File Structure

```
JARVIS/
├── app.py                          # Root JARVIS class
├── main.py                         # CLI entry point
├── AGENTS.md                       # Agent context summary
├── structure.md                    # This file
├── .env                            # Environment variables
├── core/                           # Core intelligence
│   ├── jarvis_core.py             # Central orchestrator
│   ├── brain_adapter.py           # LLM provider adapter
│   ├── brain.py                   # Core LLM interface
│   ├── router.py                  # Provider router
│   ├── planner.py                 # Intent classification
│   ├── prompt_assembler.py        # Prompt building
│   ├── tools_registry.py          # Tool registry
│   ├── tools.py                   # Built-in tools
│   ├── execution_first.py         # Execution engine
│   ├── memory.py                  # Memory system
│   ├── memory_human.py            # Human memory
│   ├── rag.py                     # RAG engine
│   ├── foods.py                   # Food engine
│   ├── context_engine.py          # Context resolution
│   ├── events.py                  # Event types
│   ├── toolcall_parser.py        # Tool call parser
│   ├── thinking_middleware.py    # Thinking block parser
│   ├── safety.py                  # Safety layer
│   ├── learning_engine.py         # Failure learning
│   ├── knowledge_graph.py         # Knowledge graph
│   ├── goal_manager.py            # Goal tracking
│   ├── world_state.py             # Environment state
│   ├── profiles.py                # Response profiles
│   ├── conversation_store.py     # Conversation persistence
│   ├── vision_engine.py           # Vision capabilities
│   └── performance_manager.py     # Performance adaptation
├── interface/                      # User interfaces
│   ├── cli.py                     # CLI interface
│   ├── desktop.py                 # Desktop monitor
│   ├── speech.py                  # Speech facade
│   └── telephony/                 # Telephony system
│       ├── config.py             # Telephony config
│       ├── twilio_server.py       # Twilio server
│       ├── call_manager.py       # Call management
│       ├── session.py            # Call session
│       ├── speech.py             # STT abstraction
│       ├── streaming.py          # Audio streaming
│       ├── logger.py             # Call logging
│       └── cli_display.py         # CLI display
├── speech/                         # Speech system
│   ├── speech_engine.py           # Speech orchestrator
│   ├── config.py                  # Speech config
│   ├── recognizer.py              # STT chain
│   ├── vad.py                     # VAD chain
│   ├── edge_provider.py           # Edge-TTS
│   ├── endpoint_detector.py       # Endpoint detection
│   ├── playback.py                # Audio playback
│   ├── streaming.py               # Utterance grabbing
│   ├── interrupt_manager.py      # Barge-in control
│   ├── queue.py                   # Speech queue
│   ├── cache.py                   # Audio cache
│   ├── events.py                  # Speech events
│   ├── logger.py                  # Conversation logging
│   └── benchmark.py               # Latency recording
├── jarvis-desktop/                 # Desktop application
│   ├── backend/
│   │   └── app.py                 # FastAPI backend (port 8001)
│   ├── frontend/
│   │   └── src/
│   │       └── App.tsx            # React frontend
│   └── electron/
│       └── main.js                # Electron wrapper
├── memory/                         # Memory storage
│   ├── facts.json
│   ├── preferences.json
│   ├── goals.json
│   ├── projects.json
│   ├── relationships.json
│   ├── episodic.json
│   ├── knowledge_graph.json
│   ├── mistakes.json
│   └── patterns.json
├── data/                           # Data storage
│   ├── memory_human/              # Human memory
│   ├── nlp_learning/             # Learning data
│   ├── nlp_user_profile/         # User profile
│   └── vector_store/             # Vector index
├── foods/                          # Prompt instructions
│   ├── 00_identity.md
│   ├── 01_reasoning.md
│   └── ... (22 files)
├── docs/                           # Documentation
│   ├── api.md
│   ├── architecture.md
│   └── ...
├── tests/                          # Test suite
│   ├── test_toolcall_parser.py
│   ├── test_tool_execution_repair.py
│   ├── test_agent_loop_repair.py
│   └── ...
└── convo/                          # Conversation logs
    └── phone/                     # Phone transcripts
```

---

## Security Considerations

### API Security
- Currently no authentication (development mode)
- CORS enabled for all origins
- Should be restricted in production

### Tool Safety
- Safety layer for high-risk operations
- Confirmation required for dangerous tools
- 45-second timeout prevents hanging

### Data Privacy
- Local memory storage (JSON files)
- No cloud data persistence
- Conversation logs stored locally

### Environment Variables
- API keys stored in .env (not committed)
- Ngrok URLs for remote access
- Should use secrets management in production

---

## Troubleshooting

### Common Issues

**JARVIS not responding:**
- Check if Ollama is running
- Verify ngrok tunnel is active
- Check .env configuration

**High latency:**
- Ollama model loading (first request slow)
- Network issues with ngrok
- Switch to Groq fallback

**Memory issues:**
- Check RAM usage
- Disable heavy features (vision, local LLM)
- Clear conversation history

**Telephony issues:**
- Verify Twilio credentials
- Check ngrok tunnel accessibility
- Validate webhook URL configuration

---

## Version Information

**Current Version:** 3.0
**Last Updated:** 2026-08-18
**Architecture:** Execution-first with multi-provider support
**Active Model:** jarvis-agi (custom fine-tuned via Ollama)
**Fallback Model:** llama-3.1-8b-instant (Groq)

---

## Contact & Support

**Developer:** Abhinav Yadav
**Location:** Dostpur, Azamgarh, UP, India
**Project:** JARVIS AI OS
**Documentation:** See `docs/` directory
**Issues:** Check AGENTS.md for current task status

---

## Summary for n8n Integration

### Quick Start
1. **Chat Integration:** Use `POST http://localhost:8001/api/chat`
2. **System Monitoring:** Use `GET http://localhost:8001/api/system-stats`
3. **Real-time:** Use `WS ws://localhost:8001/ws`
4. **Phone Calls:** Use Telephony server on port 8100

### Key Points
- **Port 8001:** Main API endpoint
- **Port 8100:** Telephony endpoint
- **Ollama via ngrok:** Primary LLM
- **Groq:** Fallback LLM
- **No Auth:** Currently open (dev mode)
- **JSON:** All responses in JSON format
- **Streaming:** SSE available for real-time responses
- **WebSocket:** Available for real-time communication

### Recommended n8n Nodes
- HTTP Request (for REST API)
- WebSocket (for real-time)
- Poll (for system stats)
- Webhook (for receiving events)
- Function (for request/response processing)

---

*This document provides a complete overview of the JARVIS AI OS structure for integration purposes. For specific implementation details, refer to the source code and individual module documentation.*
