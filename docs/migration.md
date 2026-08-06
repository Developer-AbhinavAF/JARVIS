# System Migration Plan

## Goals
Consolidate legacy implementations into `core/jarvis_core.py` using `BrainAdapter`, `PromptAssembler`, and `ThinkingMiddleware`.

## Action Steps
1. Redirect CLI and Desktop backends to `jarvis_core`.
2. Connect `ThinkingMiddleware` to the event stream.
3. Migrate file stores into `memory/`.
4. Enforce background workers for all heavy tasks.
