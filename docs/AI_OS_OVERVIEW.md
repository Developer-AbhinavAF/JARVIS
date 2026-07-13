# JARVIS AI Operating System — Overview

This document outlines the AI OS architecture scaffolded under `jarvis/ai_os`.

Key principles:
- All LLM access goes through the AI Router in `jarvis.router_service` (v3.0 multi-provider).
- Modular subsystems: `nlp`, `ml`, `cv`, `audio`, `agents`, `tools`, `memory`, `rag`.
- Plugin-friendly registries and a central `AIOS` facade in `jarvis.ai_os.core`.

This repository contains a minimal NLP pipeline (`NLPPipeline`) demonstrating how
higher-level capabilities should delegate to `router_client` without embedding
provider-specific logic.

The AI Router v3.0 replaces the former 9Router proxy with direct connections
to 20+ AI providers, including OpenAI, Anthropic, Gemini, Groq, and many more.

Next steps: implement the remaining subsystems as pluggable modules and add
integration tests, monitoring, and CI.
