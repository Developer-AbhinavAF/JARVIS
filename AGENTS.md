# JARVIS AI OS — Anchored Context Summary

## Objective
- Implement and debug full duplex Twilio Voice call integration, tool-calling, code execution fallback, NASA visual intelligence, and comprehensive runtime/tool-calling/foods system repair for the JARVIS AI OS.
- Intelligent live logging terminal (TerminalRenderer) and comprehensive QA verification/testing of the entire system.
- **Current focus (COMPLETE)**: Tool calls now execute (native + JSON-as-text) through a single validated path; resource monitor fully isolated from conversation; 64 new tests added; full suite run twice with identical results.

## Important Details
- **DO NOT** rewrite existing architecture, execution engine, memory pipeline, or speech pipeline unless required.
- Twilio integration must be plug-and-play under `interface/telephony/`.
- Ollama accessed via ngrok: `https://kiersten-nonpunishable-carry.ngrok-free.dev`
- User's Twilio ngrok: `https://scolding-delusion-surreal.ngrok-free.dev`
- `.env` has Groq API keys, Twilio creds, NASA_API_KEY, Anthropic/OpenAI/Mistral/OpenRouter keys.
- Routing fix: conversation/writing/knowledge MUST go to LLM directly; only explicit external actions trigger tools.
- PowerShell does not support `&&` — must use `;` or separate commands. No `head` command — use Python or `Select-String`. PS 5.1: `*>` merges child stderr with `NativeCommandError` banner noise.
- **Active model**: `jarvis-agi` (custom fine-tuned JARVIS AGI)
- **Suite status**: `pytest tests --ignore=tests/test_interface_consistency.py --ignore=tests/test_simple_consistency.py` → **362 passed, 22 failed, 26 skipped (both runs, identical)**. The two ignored files are pre-branch script-style tests that `import get_core` (never existed in `core/jarvis_core.py`) and wrap `sys.stdout` (causes pytest capture teardown `I/O operation on closed file` — whole-session abort when included). All 22 failures are pre-existing drift/ENV noise: `_quick_test.py`+`test_qwen3_brain.py` (pytest-asyncio not installed), `test_tools.py::test_adjust_volume` (AudioDevice COM 'Activate'), `tests/telephony/*` (Twilio config expectations), speech suites (`InterruptManager.feed_mic_signal`/`SentenceSplitter`/`EndpointDetector` API drift). NONE touch tool-calling/resource scope (git-verified untouched files).

## Architecture Changes (This Task)

### Tool Execution Contract (new)
- **ToolCall** canonical form: `name`, `arguments` (dict), `call_id` (optional). Only structured tool-call JSON with a registered tool + schema-valid args may execute; unknown/malformed JSON stays ordinary LLM text.
- **core/toolcall_parser.py** (new): `ToolCallParser` — one canonical path: native chunks (BrainAdapter) → structured ToolCall; JSON-in-text (bare/embedded/fenced/OpenAI-wrapped/legacy `name({...})`/`name("arg")`) → brace-matching + strict validation; stringified `"arguments"` JSON parsed back; dedup by (name, sorted-args). Registry looks up via `resolve_name`.
- **core/brain_adapter.py**: streamed `tool_calls` fragment accumulation (Ollama `message.tool_calls`, Groq `delta.tool_calls`) into ToolCall objects via `tool_call_sink`; starts/ends/tool calls dtype counters; malformed fragments dropped. `chat_with_tools` falls back to parser for JSON-in-text.

### Deterministic multi-command guard (core/tools_registry.py)
- `route_fast_path` returns None when input contains `and/then/also + open|launch|search|...` → chained commands fall to the agent loop (LLM plans both steps).
- Fast-path status patterns (`what is my CPU usage`, `system status`, …) tolerate trailing `?`.

### Resource monitor isolation (core/performance_manager.py + core/jarvis_core.py)
- `adapt_parameters()` returns `(max_tokens, top_k_rag)` unchanged — throttling REMOVED. `check_system_load()` is diagnostics-only; nothing injects cpu/ram values into prompts.
- **jarvis-desktop/backend/app.py `get_desktop_food()`** no longer emits `cpu_percent`/`memory_percent` (channel string only).
- Explicit system-status queries route to new **`get_system_status`** tool (aliases, lightweight psutil, `data_returned` verification) via planner `_SYSTEM_STATUS_PATTERNS` + fast path; never triggered by normal chat (verified by tests).

### Executor (core/jarvis_core.py)
- `_execute_tool_call()` — single canonical execution path: `ExecutionEvent` → `tool_registry.execute` (45s timeout) → `VerificationEvent` → assistant `tool_calls` + `tool` messages appended (args/results JSON-serialized) → NASA visual events inline.
- Agent loop: `MAX_AGENT_ITERATIONS=8`; `tool_calls` results loop; text-fallback parse gated by `plan.requires_tools`; `_final_text_is_pure_tool_call` safety net reduces pure tool JSON finals; `[USER]/[ROUTER]/[EXECUTOR]/[VERIFY]/[RESPONSE]` debug logs; LLM-visible tool messages include failure JSON so the model responds truthfully.

## Task Status
- ✓ 4 new suites: `test_toolcall_parser.py` (21), `test_tool_execution_repair.py` (23), `test_agent_loop_repair.py` (12), `test_resource_independence.py` (8) = **64 tests, all pass** (native/JSON-text/stringified-args/legacy/fenced, no-leak guarantee, failure-fed-back, fast-path routing incl. multi-command guard, 100%-CPU essay still full-length, desktop food clean, explicit system-status only).
- ✓ Full suite ×2 identical (see Important Details).
- ✓ Temp smoke scripts under `C:\Users\ender\AppData\Local\Temp\opencode\*.py` cleaned.

## Live Test Results (prior)
- ✓ "hello"/"how are you"/"what is Python" → No tools, normal LLM response
- ✓ "open youtube"/"open gmail" → browser; "open notepad" → launches app
- ✓ "search gamerfleet on google" → web search; "find pictures of mars" → NASA images

## Next Move
1. Optional: verify `get_system_status` end-to-end via desktop UI ("what is my CPU usage").
2. Re-check when Ollama ngrok is back: `brain_adapter` native tool-call ingestion against live jarvis-agi HTTP stream.
3. If desired: reconcile the pre-existing drift suites (speech `InterruptManager.feed_mic_signal`, telephony config expectations, `get_core` import in the two script files) in a NESTED follow-up — out of scope for the tool-call task.

## Relevant Files
- `core/toolcall_parser.py` (new): insert/validate JSON-as-text; `parse_text()` gates execution.
- `core/brain_adapter.py`: sinks/tool_calls, `chat_with_tools`, LLMResult/ToolCall.
- `core/tools_registry.py`: `validate_tool_call`, multi-command guard, `route_fast_path` (system-status `\??\s*$`), `get_system_status`.
- `core/jarvis_core.py`: `_execute_tool_call` (lines ~90), agent loop (~404), `_final_text_is_pure_tool_call` (~179).
- `core/planner.py`: `_SYSTEM_STATUS_PATTERNS` (before memory patterns), `_EXTERNAL_ACTION_PATTERNS` unanchored `open ` etc.
- `core/performance_manager.py`: `adapt_parameters` passthrough (was THROTTLED — now inert).
- `jarvis-desktop/backend/app.py`: `get_desktop_food()` clean.