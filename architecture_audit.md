# JARVIS Architecture Audit

**Date:** 2026-07-15
**Auditor:** Automated code inspection
**Scope:** Full system — app.py, backend, NLP, execution, memory, frontend

---

## Executive Summary

The system has **two working end-to-end paths**:

1. **NLP → Tool Execution** (fast-path intents): hello, open_app, joke, datetime, search, etc.
2. **NLP → LLM Fallback** (when no tool/response available): uses AIRouter

Everything else is either import-only (never called from `handle()`), has broken method signatures, or is frontend-only mock data.

---

## Subsystem Status

### 1. app.py Initialization

| Field | Detail |
|-------|--------|
| **Status** | **CONNECTED** |
| **Entry** | `JARVIS.__init__()` → `JARVIS.boot()` → `JARVIS.handle()` |
| **What it does** | Creates infrastructure singletons (events, state, settings, benchmarks, analytics). Boot validates 22 subsystems. `handle()` is the sole input pipeline. |
| **Boot validation** | Infrastructure: pass-through checks. NLP: actually runs `process("hello")`. Execution: checks tool count. Memory: instantiates `JarvisMemory()`. Other 10 subsystems: `__import__()` only. |
| **Used by** | `jarvis-desktop/backend/app.py` creates JARVIS, calls `boot()` then `handle()` |
| **Manual test** | `python app.py` → should print 22/22 Checks Passed |
| **Failure conditions** | If NLP or Execution fail to import, boot reports DEGRADED. Memory failure is non-critical. |

### 2. Router (AI Router)

| Field | Detail |
|-------|--------|
| **Status** | **CONNECTED** (as LLM fallback only) |
| **Entry** | `jarvis.ai_router.get_router()` → `AIRouter.chat()` |
| **What it does** | 20+ provider registry, capability detection, model selection, load balancing, fallback chain. Fully implemented. |
| **Used by** | `app.py:319` — called ONLY when no tool or NLP response is available (Step 5: LLM Fallback) |
| **Boot validation** | Import + provider count check |
| **Manual test** | `python app.py` then type a conversational question with no tool match |
| **Failure conditions** | No API key configured → all providers fail → returns error |
| **Actual latency** | Not measured (requires LLM call) |

### 3. NLP Engine

| Field | Detail |
|-------|--------|
| **Status** | **CONNECTED** |
| **Entry** | `jarvis.nlp.SemanticNLPEngine.process(text)` → `NLPOutput` |
| **What it does** | 35-phase pipeline with fast-path optimization. Fast-path skips 29 phases for 30+ known intents. |
| **Used by** | `app.py:248` — MANDATORY first step of `handle()` |
| **Boot validation** | Runs `process("hello")`, verifies intent + confidence > 0 |
| **Manual test** | `python -c "from jarvis.nlp import SemanticNLPEngine; e=SemanticNLPEngine(); print(e.process('hello').intent)"` |
| **Measured performance** | Fast-path p50: **2.0ms**, p95: **10.2ms**. Full-path p50: **7.0ms**, p95: **59.6ms** |
| **Failure conditions** | Import failure → boot fails (critical). Runtime errors caught in `handle()`. |

### 4. Planner

| Field | Detail |
|-------|--------|
| **Status** | **PARTIAL** — imported, used by NLP pipeline, but not independently |
| **Entry** | `jarvis.nlp.planner.Planner.plan()` |
| **What it does** | Multi-step task decomposition. Called from NLP Phase 16 only when `is_multi_intent` is true. |
| **Used by** | NLP pipeline only (Phase 16). Not called from `app.py` directly. |
| **Boot validation** | Import-check only |
| **Manual test** | Send compound command: "open notepad and search for tutorials" |
| **Failure conditions** | Never triggered for simple commands |

### 5. Execution Engine

| Field | Detail |
|-------|--------|
| **Status** | **CONNECTED** |
| **Entry** | `jarvis.execution.engine.ExecutionEngine.execute_from_nlp(nlp_output)` |
| **What it does** | Resolves tool from NLP intent → maps via `_intent_tool_map` → looks up in registry → builds params from entities → executes → verifies → records trace |
| **Used by** | `app.py:259` — called when `nlp_output.tool` is set (Step 2: Tool Execution) |
| **Boot validation** | Tool count check |
| **Manual test** | `python app.py` then type "open notepad" |
| **Failure conditions** | Tool not found → returns `ToolResult(success=False)`. Tool execution error → caught, returns error. |
| **Verified working** | Yes — 106 integration tests pass including `nlp→exec: 'open notepad' execution success` |

### 6. Tool Registry

| Field | Detail |
|-------|--------|
| **Status** | **CONNECTED** |
| **Entry** | `jarvis.execution.tool_registry.ToolRegistry` — singleton `tool_registry` |
| **Registered tools** | 16 tools: `open_app`, `close_app`, `web_search`, `open_url`, `create_file`, `delete_file`, `read_file`, `adjust_volume`, `take_screenshot`, `get_system_stats`, `get_time`, `get_date`, `list_running_apps`, `add_note`, `get_notes`, `add_todo`, `get_todos`, `complete_todo` |
| **What it does** | Thread-safe registry with `register()`, `get()`, `find_tools()`, `get_by_category()` |
| **Used by** | Execution engine (tool lookup), boot validation (tool count + execute fn check) |
| **Boot validation** | Iterates all tools, checks each has `execute` fn |
| **Manual test** | `python app.py` then type `tools` command |
| **Known issue** | `web_search` verification fails: `_verify_url() got an unexpected keyword argument 'query'` |

### 7. Verification Engine

| Field | Detail |
|-------|--------|
| **Status** | **PARTIAL** |
| **Entry** | `jarvis.execution.verifier.VerificationEngine` |
| **What it does** | `verify_process_running()` — psutil process scan. `verify_file_exists()` — os.path. `verify_port_listening()` — socket. `verify_window_exists()` — **STUB: only checks browser processes, not actual windows**. |
| **Used by** | Execution engine (Step 5 of `execute_from_nlp`). Boot Phase 8. |
| **Boot validation** | Import-check only |
| **Failure conditions** | `verify_window_exists()` will return False for non-browser apps. |

### 8. Memory

| Field | Detail |
|-------|--------|
| **Status** | **BROKEN** |
| **Entry** | `jarvis.memory.JarvisMemory` (instantiated at boot Phase 6) |
| **What it does** | SQLite-backed storage for conversations, preferences, todos, reminders, notes, YouTube notes. All CRUD methods exist. |
| **CRITICAL BUG** | `app.py` calls `self._memory.search(query)` (line 471) and `self._memory.store(content)` (lines 484, 493, 510). **`JarvisMemory` has no `search()` or `store()` methods.** It has `search_notes()`, `search_conversations()`, `save_conversation()`, `add_note()`. The `AttributeError` is caught by bare `except` blocks, so memory operations silently fail. |
| **Used by** | `app.py:300-316` (memory recall/store in `handle()`), `app.py:450-512` (`_handle_memory`, `_auto_save_conversation`) |
| **Boot validation** | Instantiates `JarvisMemory()` — no functional test |
| **Manual test** | `python -c "from jarvis.memory import JarvisMemory; m=JarvisMemory(); print(hasattr(m, 'search'), hasattr(m, 'store'))"` → prints `False False` |
| **Impact** | Memory recall returns "I don't have anything stored about that yet." Memory store silently fails. Auto-save silently fails. |
| **Fix required** | Add `search()` and `store()` methods to `JarvisMemory`, OR change app.py to use `JarvisMemory.search_notes()`/`JarvisMemory.save_conversation()` |

### 9. Knowledge

| Field | Detail |
|-------|--------|
| **Status** | **BROKEN** (not connected) |
| **Entry** | `jarvis.knowledge.KnowledgeEngine` — singleton `knowledge_engine` |
| **What it does** | Full RAG pipeline: `search()`, `search_semantic()`, `retrieve()`, `learn()`, `learn_document()`, `learn_url()`, `summarize()`. |
| **Used by** | **NOT called from `app.py:handle()`**. NLP Phase 12b (`nlp/__init__.py:538`) tries `from jarvis.knowledge import knowledge_engine` inline with silent exception swallowing. |
| **Boot validation** | `__import__("jarvis.knowledge")` only |
| **Impact** | Knowledge retrieval never happens. The "Knowledge" step in the priority chain (Tool > Memory > Knowledge > Reasoning > Conversation) is dead code. |
| **Manual test** | `python -c "from jarvis.knowledge import knowledge_engine; print(knowledge_engine.search('python'))"` |

### 10. Learning

| Field | Detail |
|-------|--------|
| **Status** | **PARTIAL** (used by NLP only) |
| **Entry** | `jarvis.learning.LearningEngine` — singleton `learning_engine` |
| **What it does** | 15+ sub-modules: experience DB, preferences, habits, workflows, errors, reasoning, tools, projects, personality, knowledge learning, memory optimizer, behavior adapter, self-evaluator, autonomous improver, background coordinator. |
| **Used by** | NLP pipeline Phase 23 (`self.learning.record_interaction()`). Not called from `app.py` directly. |
| **Boot validation** | `__import__("jarvis.learning")` only |
| **Impact** | Learning happens passively through NLP pipeline, but no主动 learning or improvement loop runs. |

### 11. Vision

| Field | Detail |
|-------|--------|
| **Status** | **PARTIAL** (used by NLP only) |
| **Entry** | `jarvis.vision.VisionEngine` — singleton `vision_engine` |
| **What it does** | Screen capture → OCR → UI detection → layout analysis → desktop map → event detection → memory recording. Uses pyautogui, Tesseract, win32gui. |
| **Used by** | NLP Phase 35 calls `self.vision.see()` and `self.vision.fusion.fuse()`. Not called from `app.py`. |
| **Boot validation** | `__import__("jarvis.vision")` only |
| **Failure conditions** | Requires Tesseract OCR installed. Platform-specific (Windows APIs). May fail silently. |

### 12. Speech

| Field | Detail |
|-------|--------|
| **Status** | **PARTIAL** (not connected to handle()) |
| **Entry** | `jarvis.speech.SpeechEngine` — singleton `speech_engine` |
| **What it does** | ElevenLabs TTS streaming, audio playback, speech-to-text (Whisper), interrupt handling, prosody, conversation loop. |
| **Used by** | Not called from `app.py:handle()`. Available via `nlp.create_speech_nlp()` but never invoked. |
| **Boot validation** | `__import__("jarvis.speech")` only |
| **Failure conditions** | Requires ElevenLabs API key. Whisper model download on first use. |

### 13. Desktop Intelligence

| Field | Detail |
|-------|--------|
| **Status** | **BROKEN** |
| **Entry** | `jarvis.infra.desktop.DesktopIntelligence` — singleton `desktop_intelligence` |
| **What it does** | Detects user session type (coding, study, gaming, etc.) from active windows. Background polling thread. |
| **CRITICAL STUB** | `_get_windows()` method (`desktop.py:233-250`) is a **stub**. Returns a single empty `ActiveWindow(title="", app_name="")` as fallback. Comment says "Real implementation would use platform APIs". Cannot detect anything. |
| **Used by** | Not called from `app.py:handle()`. Not started (`.start()` never called). |
| **Boot validation** | `__import__("jarvis.infra.desktop")` only |

### 14. Environment Engine

| Field | Detail |
|-------|--------|
| **Status** | **BROKEN** (not started) |
| **Entry** | `jarvis.infra.environment.EnvironmentEngine` — singleton `environment_engine` |
| **What it does** | Background thread polls CPU, RAM, disk, battery via psutil. Emits events on threshold changes. `snapshot()` returns `SystemResources`. |
| **Used by** | Not called from `app.py:handle()`. Not started (`.start()` never called). No background monitoring runs. |
| **Boot validation** | `__import__("jarvis.infra.environment")` only |

### 15. Security Layer

| Field | Detail |
|-------|--------|
| **Status** | **PARTIAL** (imported, never enforced) |
| **Entry** | `jarvis.infra.security.SecurityLayer` — singleton `security_layer` |
| **What it does** | Secret storage (base64 — not encryption), sensitive data detection via regex, text sanitization, permission system, audit logging. |
| **Used by** | Imported in `__init__` but never called during request handling. Permission system exists but is never enforced. |
| **Boot validation** | `__import__("jarvis.infra.security")` only |
| **Security note** | `store_secret()` uses base64 encoding, not encryption. This is obfuscation, not security. |

### 16. UI (Frontend)

| Field | Detail |
|-------|--------|
| **Status** | **PARTIAL** |
| **Entry** | `jarvis-desktop/frontend/src/App.tsx` → React components |
| **What it does** | Dashboard, Chat, Memory, Logs, Settings, PC Control, Docs. Electron + Vite + React + TypeScript + TailwindCSS. |

#### Frontend Component Status:

| Component | Real Data? | Functional? | Notes |
|-----------|-----------|-------------|-------|
| **ChatPanel** | Yes | **YES** | Posts to `/api/chat`, receives SSE stream with intent metadata |
| **LogsSection** | Yes | **YES** | WebSocket `/ws/logs` + REST `/api/logs`. Initial WS batch has format mismatch (dropped). |
| **DashboardSection** | Partial | **PARTIAL** | CPU/memory/battery from psutil (real but stale). Network always 0. CPU history hardcoded. NLP pipeline status hardcoded strings. |
| **RightPanel** | Partial | **PARTIAL** | Same stale data. Charts hardcoded. Plugins hardcoded. |
| **MemorySection** | No backend | **FRONTEND-ONLY** | Todos/notes/reminders stored in localStorage only. No backend API. |
| **SettingsSection** | No | **MOCK** | All `useState`. Save button does nothing. Resets on reload. |

### 17. Logs

| Field | Detail |
|-------|--------|
| **Status** | **CONNECTED** |
| **Entry** | `FrontendLogHandler` in `jarvis-desktop/backend/app.py` + `/api/logs` + `/ws/logs` |
| **What it does** | Captures Python logging records → buffers 200 entries → streams via WebSocket → frontend displays in terminal format |
| **Used by** | LogsSection.tsx fetches via REST and WebSocket |
| **Known issue** | Backend sends `{type: "batch", logs:[...]}` on WS connect, frontend only handles `{type: "log", data:...}`, dropping initial batch |

### 18. Settings

| Field | Detail |
|-------|--------|
| **Status** | **BROKEN** (frontend) / **CONNECTED** (backend) |
| **Backend** | `jarvis.infra.settings.SettingsStorage` — JSON file persistence. Used by `app.py` shutdown. |
| **Frontend** | `SettingsSection.tsx` — all `useState`, no backend API, no persistence. Entirely cosmetic. |
| **Gap** | No `/api/settings` endpoint exists. Frontend settings never reach backend. |

### 19. Dashboard

| Field | Detail |
|-------|--------|
| **Status** | **PARTIAL** |
| **Backend** | `/api/system-stats` returns real psutil data. `/ws` pushes every 2 seconds. |
| **Frontend** | Receives stats via WebSocket. CPU/memory/battery real. Network always 0 (backend hardcodes 0). CPU history array is hardcoded 7-point, not accumulated. |
| **NLP Pipeline section** | Entirely hardcoded strings ("Active", "<300ms", "35+", "18"). No data source. |

### 20. SSE Events

| Field | Detail |
|-------|--------|
| **Status** | **CONNECTED** |
| **Backend** | `/api/chat` with `stream=true` returns SSE with token-by-token delivery + final `done` event containing actions/intent/confidence/tool/verified/total_ms |
| **Frontend** | ChatPanel.tsx reads SSE stream, extracts metadata, stores in message |
| **WebSocket** | `/ws` pushes `system_stats` every 2s. `/ws/logs` pushes log entries in real-time. |

### 21. Health Checks

| Field | Detail |
|-------|--------|
| **Status** | **CONNECTED** |
| **Backend** | `/api/health` returns `{status, initialized, nlp_ready, execution_ready, memory_ready, benchmarks, analytics}` |
| **Frontend** | Not called from any component. |
| **Boot** | `JARVIS.get_health()` returns dict with boot_complete, nlp_ready, execution_ready, router_ready, memory_ready, benchmarks, analytics |

---

## Data Flow Diagram

```
User Input
    │
    ▼
[Frontend ChatPanel] ──POST /api/chat──► [Backend app.py]
                                              │
                                              ▼
                                     [JARVIS.handle()]
                                              │
                    ┌─────────────────────────┤
                    │                         │
                    ▼                         ▼
          [NLP Engine]                [AI Router] (fallback)
          process(text)               chat(text)
                    │                         │
                    ▼                         │
          NLPOutput                        │
          .intent                          │
          .tool                            │
          .confidence_score                │
          .response_text                   │
          .parameters                      │
                    │                         │
          ┌─────────┤                         │
          │         │                         │
          ▼         ▼                         ▼
    [Tool in    [No tool]              [LLM Response]
     registry]       │
          │          ▼
          │    [NLP response_text]
          │    (greetings, jokes)
          │          │
          ▼          │
    [Execution      │
     Engine]        │
     execute_from_nlp()
          │          │
          ▼          ▼
    [ToolResult] ──► Response ──► [Backend builds JSON]
                                        │
                                        ▼
                               [Frontend displays]
```

---

## Broken Connections (Priority Order)

### CRITICAL

1. **Memory `search()`/`store()` missing** — `app.py` calls methods that don't exist on `JarvisMemory`. Memory recall/store silently fails. Fix: add methods or change caller.

### HIGH

2. **Desktop Intelligence `_get_windows()` is a stub** — returns empty data. Cannot detect user activity.
3. **Environment Engine not started** — `.start()` never called. No background monitoring.
4. **Knowledge not connected to `handle()`** — RAG retrieval never happens. Priority chain step 3 is dead.
5. **Security not enforced** — Permission system exists but is never checked during tool execution.

### MEDIUM

6. **Frontend Settings entirely cosmetic** — No persistence, no backend API.
7. **Frontend Memory is localStorage-only** — No backend sync, no API.
8. **Dashboard NLP pipeline status is hardcoded** — No real data source.
9. **Dashboard CPU history is hardcoded** — Not accumulated from real data.
10. **Dashboard network speed always 0** — Backend hardcodes zeros.
11. **LogsSection initial WS batch dropped** — Format mismatch: `batch` vs `log`.
12. **File upload returns stub** — "File analysis not yet wired to new engine."
13. **Web search verification broken** — `_verify_url() got an unexpected keyword argument 'query'`

### LOW

14. **Frontend hooks `useSystemStats`, `useExecuteCommand` are dead code** — Never called.
15. **Frontend plugins are hardcoded** — Never fetched from backend.
16. **Frontend learning/shopping progress events** — Backend never sends them.
17. **Speech not connected** — Requires ElevenLabs API key, never invoked from handle().
18. **Vision depends on Tesseract** — May not be installed.

---

## What Actually Works End-to-End

| Path | Status | Evidence |
|------|--------|----------|
| "hello" → NLP → GREETING → response | **WORKS** | 106 tests pass, p50=2.0ms |
| "open notepad" → NLP → OPEN_APP → tool.execute() → verified | **WORKS** | 106 tests pass, psutil confirms process |
| "search for X" → NLP → SEARCH_WEB → web_search.execute() | **WORKS** (verify fails) | Tool executes, verification warning |
| "what time is it" → NLP → DATETIME → response | **WORKS** | 106 tests pass |
| "tell me a joke" → NLP → JOKE → response | **WORKS** | 106 tests pass |
| Conversational question → NLP (no tool) → LLM fallback | **WORKS** | Requires configured LLM provider |
| Memory recall → NLP → RECALL_MEMORY → JarvisMemory.search() | **BROKEN** | AttributeError silently caught |
| Memory store → NLP → SAVE_MEMORY → JarvisMemory.store() | **BROKEN** | AttributeError silently caught |
| Knowledge retrieval → NLP Phase 12b → knowledge_engine.retrieve() | **BROKEN** | Never connected to handle() |
| Dashboard → WebSocket → system_stats | **WORKS** | Real psutil data, pushed every 2s |
| Chat → POST /api/chat → SSE stream | **WORKS** | Full intent metadata in response |
| Logs → WebSocket /ws/logs | **WORKS** | Real-time log streaming |

---

## Performance (Measured)

| Operation | p50 | p95 | Notes |
|-----------|-----|-----|-------|
| NLP fast-path (hello) | 2.0ms | 10.2ms | 20 iterations |
| NLP full-path (weather) | 7.0ms | 59.6ms | 10 iterations |
| Boot time | 47.3s | — | 22 subsystems, Whisper model load |
| WebSocket stats push | 2s | — | Backend interval |

---

## Summary

| Metric | Count |
|--------|-------|
| Total subsystems | 22 |
| CONNECTED (working end-to-end) | 7 (app.py, NLP, Execution, Tool Registry, Router, Logs, SSE) |
| PARTIAL (imported but limited use) | 6 (Planner, Verification, Learning, Vision, Dashboard, Memory frontend) |
| BROKEN (methods missing or stubs) | 4 (Memory backend, Desktop Intelligence, Environment, Security enforcement) |
| MOCK/COSMETIC (no real functionality) | 2 (Settings frontend, NLP pipeline dashboard display) |
| NOT CONNECTED (import-only) | 3 (Knowledge, Speech, Agents) |
