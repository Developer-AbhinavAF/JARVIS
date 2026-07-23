# JARVIS Architecture Audit

**Generated:** 2026-07-19  
**Scope:** Full repository scan — active code under `core/`, `interface/`, `vision/`, `tests/`, `jarvis-desktop/`, `data/`  
**Phase:** 1 — Audit only (no code changes)

---

## Executive Summary

JARVIS has been **partially migrated** to an LLM-driven flat layout (`core/` + `interface/` + `vision/`). The legacy `jarvis/` package (47+ files, regex NLP, keyword routers) is **no longer on disk**, but its artifacts remain in `data/`, documentation, and stale test references.

The active system is **not yet human-level**. It mixes LLM intent classification with **keyword matching, hardcoded responses, and fake verification** in critical paths. Tool selection is mislabeled as "semantic" but uses substring keyword overlap, not vector embeddings.

**Mission compliance:** ❌ FAIL — multiple explicit violations of the no-regex / no-keyword / no-hardcoded-response rules remain in production code.

---

## Current Architecture

```
User Input
    │
    ▼
interface/cli.py  OR  jarvis-desktop/backend/app.py (broken import)
    │
    ▼
interface/app.py  (JARVIS.handle)
    │
    ├─► core/nlp_llm.py
    │       ├─ ContextEngine (20-turn in-memory history, pronoun resolution)
    │       ├─ LLM intent classification  (router.chat)
    │       ├─ LLM entity extraction      (router.chat)
    │       └─ _map_to_tool()             (hardcoded intent→tool + keyword selector)
    │
    ├─► core/execution.py  (execute_from_nlp)
    │
    └─► core/tools.py + core/tools_enhanced.py  (~40 registered tools)
            │
            ├─ core/memory_json.py      (JSON persistence)
            ├─ core/knowledge_semantic.py (ChromaDB — booted, not wired to pipeline)
            ├─ vision/vision.py         (capture + OCR)
            └─ interface/speech.py      (ElevenLabs → pyttsx3, Whisper STT)
```

### Entry Points

| File | Role | Status |
|------|------|--------|
| `main.py` | Delegates to `interface.cli.main()` | ✅ Active |
| `interface/cli.py` | Text / Speech / Debug modes | ✅ Active |
| `interface/app.py` | `JARVIS` orchestrator | ✅ Active |
| `jarvis-desktop/backend/app.py` | FastAPI on port 8001 | ❌ Broken — imports missing `app.py` at repo root |

### Core Modules (31 Python files)

| Module | Purpose |
|--------|---------|
| `core/nlp_llm.py` | LLM intent + entity extraction, context, tool mapping |
| `core/router.py` | Multi-provider LLM fallback (Groq → Mistral → OpenAI → Ollama) |
| `core/tools.py` | 26 core tools + registry |
| `core/tools_enhanced.py` | 14 enhanced tools (system control, clipboard, mouse/keyboard) |
| `core/execution.py` | Tool execution with tracing |
| `core/memory_json.py` | JSON memory (memories, mistakes, knowledge, conversation) |
| `core/knowledge_semantic.py` | ChromaDB semantic knowledge (fallback keyword search) |
| `core/semantic_tool_selector.py` | "Semantic" tool selection (**keyword-based**) |
| `core/tool_selector.py` | Duplicate tool selector (**unused**) |
| `interface/speech.py` | TTS/STT |
| `interface/desktop.py` | System monitor |
| `vision/vision.py` | Screenshot + OCR |

---

## Mission Violations (Must Remove)

### 1. Keyword Matching in NLP / Memory Path

| Location | Violation |
|----------|-----------|
| `core/tools.py:451-470` | `save_memory()` — keyword patterns: `'my name is'`, `'mera naam'`, `'i like'`, etc. |
| `core/tools.py:485-513` | `recall_memory()` — `if q in ('who am i')`, `if key in q`, `if 'where' in q and 'live' in q` |
| `core/memory_json.py:108-118` | `search_memories()` — substring keyword match on key/value |
| `core/memory_json.py:175-186` | `search_knowledge()` — substring keyword match |
| `core/knowledge_semantic.py:137-155` | `_keyword_search()` fallback |
| `core/semantic_tool_selector.py:63-66` | `if keyword in query_lower` |
| `core/tool_selector.py:80-102` | Word-overlap keyword similarity (**dead code, but present**) |
| `generate_tool_embeddings.py:212-213` | Explicit placeholder: "simple keyword matching" |

### 2. Regex Usage

| Location | Usage |
|----------|-------|
| `core/tools.py:519-520` | `re.search(r'(\d+)', q)` for "N prompts ago" in `recall_memory()` |

### 3. Hardcoded Responses

| Location | Response |
|----------|----------|
| `core/nlp_llm.py:342` | `"Hello! How can I help you today?"` on GREETING |
| `core/tools.py:474` | `"Got it! I'll remember that ..."` |
| `core/tools.py:494` | `"I don't have information about you yet..."` |
| `core/tools.py:505,513` | `"I don't know your {key} yet."` / location variants |
| `core/tools.py:546,549,554` | Delete-memory prompt strings |
| `core/tools.py:641,643` | `"I don't have an answer for that right now."` |
| `interface/app.py:190-227` | Per-tool hardcoded reply templates in `handle()` |

### 4. Hardcoded Intent → Tool Routing

| Location | Issue |
|----------|-------|
| `core/nlp_llm.py:367-447` | 80-line `if intent == ...` mapping dict |
| `core/tool_selector.py:112-131` | Duplicate `intent_tool_map` (**unused**) |

### 5. Fake Tool Verification

| Location | Issue |
|----------|-------|
| `core/tools.py:119-120` | `verify_url_loaded()` always returns `True`, never called |
| `core/tools.py:209-210` | `open_url()` — `verified=True` without checking browser/tab |
| `core/tools.py:225-226` | `web_search()` — opens URL, no verification |
| `core/tools_enhanced.py:56` | `ConfirmationHandler` auto-confirms `return True` |
| `core/tools_enhanced.py:343-352` | `open_first_result()` — stub, always fails |

---

## NLP Pipeline Gap vs Target (Phase 2 Spec)

**Current:** Two separate LLM calls (intent string, then entity JSON). No unified strict JSON schema.

**Required:**
```json
{
  "intent": "",
  "entities": {},
  "requires_tool": true,
  "tool_category": "",
  "confidence": 0.0,
  "execution_plan": [],
  "memory_required": true,
  "clarification_required": false
}
```

**Missing capabilities:**
- Single structured NLP response
- Last **15** messages in prompt (currently 3 via `get_recent_context(n=3)`)
- Active windows injected into NLP context
- Memory injected into NLP prompt (semantic retrieval)
- Multi-step `execution_plan` (e.g., OPEN_WEBSITE + SEARCH_YOUTUBE)
- Hinglish/Hindi examples handled purely via LLM (partially works, undermined by keyword fallbacks)

---

## Tool Selection Gap vs Target (Phase 3 Spec)

**Current:**
- `tool_embeddings.json` contains keywords + metadata, **no vector embeddings**
- `generate_tool_embeddings.py` admits placeholder keyword matching
- `semantic_tool_selector.match_tool()` uses substring keyword overlap
- LLM never receives a filtered top-5 tool list

**Required:**
- Real embeddings per tool (name, description, examples)
- Runtime embedding search → top 5 tools → send only those to LLM
- Target latency: **<20ms**

---

## Memory Gap vs Target (Phase 4 Spec)

**Current structure** (`memory_json.py`):
```json
{ "key": { "value": "...", "confidence": 0.8, "updated_at": "..." } }
```

**Required structure:**
```json
{ "fact": "My name is Abhinav", "type": "name", "timestamp": "", "importance": 10 }
```

**Gaps:**
- No ChromaDB/FAISS semantic search for user memories
- `recall_memory()` uses keyword/key lookup, not embedding retrieval
- `semantic_knowledge` (ChromaDB) is booted in `JARVIS.boot()` but **never called** in `handle()`
- Dual context: `ContextEngine` (session) vs `conversation_history.json` (persistent) — not unified
- `delete_memory()` calls `search_memories(query, limit=10)` but `search_memories()` accepts no `limit` arg → **runtime bug**

---

## Context Gap vs Target (Phase 5 Spec)

**Current `ContextEngine` tracks:**
- last_message, last_response, last_tool, last_entities, last_intent
- 20-turn history
- Basic pronoun resolution (`it`, `this`, `that`, `there`)

**Missing:**
- active_app, previous_app, previous_website, previous_song
- previous_image, previous_screenshot, previous_command
- Context not passed to LLM as structured state
- Pronoun resolution is string replace on first entity only — fragile

---

## Tools Gap vs Target (Phase 6 Spec)

### Implemented (partial)

| Category | Tools | Verification Quality |
|----------|-------|---------------------|
| Browser | `open_url`, `web_search`, `open_first_result` (stub) | Low — no tab verification |
| Apps | `open_app`, `close_app` | Medium — process check |
| Vision | `take_screenshot`, `screen_analysis`, `show_image` | Medium — file exists |
| Memory | `save_memory`, `recall_memory`, `delete_memory` | Keyword-based, not semantic |
| System | `get_system_stats`, volume, brightness, sleep/shutdown/lock | Mixed |
| Desktop | `get_active_app`, `list_running_apps`, mouse/keyboard | Low — no post-action verify |
| Media | `play_media`, `play_media_advanced` | Opens browser, no playback verify |
| Files | create/read/delete + safe variants | Good for file ops |
| Utility | time, date, calculate, ask_ai, clipboard, email | Basic |

### Not Implemented

| Required Tool | Status |
|---------------|--------|
| Weather | ❌ Missing |
| Jokes | ❌ Missing |
| Notifications | ❌ Missing |
| Camera (dedicated tool) | ⚠️ Partial — in APP_MAP only |
| Hotkeys | ❌ Missing (`press_key` exists, no combo/hotkey tool) |
| File manager | ❌ Missing |
| Folder manager | ❌ Missing |
| Search GitHub (dedicated) | ⚠️ Via generic web_search + site param |
| Semantic memory search tool | ❌ Missing |
| Kokoro TTS | ❌ Missing (ElevenLabs → pyttsx3 only) |

---

## Vision Gap (Phase 7)

**Implemented:** capture, OCR, basic `analyze_screen()`  
**Missing:** LLM screen understanding, active-window analysis tool, "summarize screen" via vision model  
**Gap:** `screen_analysis` returns raw OCR snippet, not semantic understanding

---

## Speech Gap (Phase 8)

| Priority | Engine | Status |
|----------|--------|--------|
| 1 | ElevenLabs | ✅ Implemented |
| 2 | Kokoro | ❌ Not implemented |
| 3 | pyttsx3 | ✅ Fallback |

Speech mode exists in CLI but STT quality flagged as poor in `manual_test.md`.

---

## Test & Documentation Drift

| Artifact | Issue |
|----------|-------|
| `tests/test_nlp.py` | References `Intent.OPEN_WEBSITE`, `SEARCH_WEB`, `RECALL_MEMORY` — **enum values don't exist** in `nlp_llm.py` |
| `tests/test_memory.py` | Calls `json_memory.store()`, `update()`, `delete()` — **API doesn't exist** |
| `tests/test_knowledge.py` | Calls `learn()`, `retrieve()`, `search()` — **API doesn't exist** |
| `_quick_test.py` | Uses removed APIs |
| `README.md` | Documents removed `jarvis/` package structure |
| `architecture_audit.md` (prior) | References removed `core/nlp.py`, `core/memory.py` |
| `jarvis-desktop/backend/app.py` | Imports `JARVIS_ROOT / "app.py"` — file missing |

---

## Legacy Data (Not Wired to Active Code)

| Path | Contents |
|------|----------|
| `data/nlp_learning/` | Command stats, frequencies, unknown commands |
| `data/cognitive_experiences.json` | Old intent telemetry |
| `data/nlp_user_profile/user_profile.json` | Legacy user profile |
| `data/scheduled_tasks.json` | Unused |
| `data/projects.json` | Unused |

---

## Recommended Migration Order (Phases 2–10)

1. **Replace NLP pipeline** — single LLM call, strict JSON, 15-message context + memory + active windows
2. **Remove all keyword/regex from memory tools** — semantic retrieval via ChromaDB/FAISS
3. **Implement real tool embeddings** — replace keyword selectors; delete `tool_selector.py`
4. **Expand ContextEngine** — track apps, websites, screenshots, songs
5. **Wire verification** — browser tab checks, no fake `verified=True`
6. **Implement missing tools** — weather, jokes, folders, hotkeys, notifications, camera
7. **Fix tests** — align with new APIs; generate 100 manual tests
8. **Fix desktop backend** — point to `interface/app.py`
9. **Delete legacy data/scripts** — `data/nlp_learning/`, stale audit docs after migration
10. **Performance profiling** — measure against targets (see `performance_report.md`)

---

## File Inventory Summary

| Category | Count |
|----------|-------|
| Active Python modules | 31 |
| Registered tools | ~40 |
| Test modules | 10 (+ 4 dev scripts) |
| Audit/report markdown (pre-existing) | 16 |
| Legacy data JSON dirs | 3 |

**Verdict:** Architecture foundation exists but is **hybrid LLM + keyword**. Full migration required before mission completion.
