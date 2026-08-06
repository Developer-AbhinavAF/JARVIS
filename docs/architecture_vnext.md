# JARVIS vNext++ Ultimate Architecture Specification

## Overview
JARVIS vNext++ is an event-driven, execution-first local AI Operating System designed for low-end host hardware (Intel i5 6th Gen CPU-only, 8GB RAM).

## 22-Step Execution Pipeline
```
User Query ──► 1. Normalizer ──► 2. Language Detection ──► 3. Intent Detection ──► 4. Entity Extraction
   │
   ▼
5. Context Resolution ──► 6. World State ──► 7. Hybrid Memory ──► 8. Knowledge Graph ──► 9. RAG Search
   │
   ▼
10. Planner ──► 11. Goal Manager ──► 12. Skill Manager ──► 13. Candidate Tool Search ──► 14. LLM Decision
   │
   ▼
15. Execution ──► 16. Verification ──► 17. Reflection ──► 18. Learning ──► 19. Event Bus
   │
   ▼
20. Natural Response ──► 21. Speech Output ──► 22. World State Update
```

## Key Architectural Systems
1. **Pure Brain Layer**: LLM handles reasoning and planning only; never directly executes OS actions.
2. **Deterministic Planner**: Evaluates memory, RAG, skills, and tools; builds multi-step execution plans with confidence ratings.
3. **World State Engine**: Tracks active app, window, website, folder, clipboard, selection, focus, processes, and hardware status.
4. **Goal Manager**: Manages persistent long-term, short-term, daily, and project goals.
5. **Workflow Skill System**: Multi-step composable workflows (skills calling skills and tools).
6. **9-Tier Hybrid Memory**: Multi-level lookup from Session Cache (<1ms) to Facts (<5ms) to Semantic Search.
7. **Episodic Memory**: Remembers user & system experiences (date, context, outcome, lessons learned).
8. **Knowledge Graph**: Entity-relationship graph retrieval for fast context navigation.
9. **Confidence Engine**: Assigns confidence ratings to decisions and prompts user if confidence < 30%.
10. **Reflection & Learning Engine**: Tool failures emit `LearningEvent` objects to store lessons in `memory/mistakes.json`.
11. **Unified Event Bus**: All interfaces (CLI, Desktop, API, Speech, Mobile, Web) consume identical typed event streams.
12. **Centralized Thinking Middleware**: Brain parses `<think>` tags into `ThinkingEvent` objects; UI displays dimmed text.
13. **Self Diagnostics & Startup Optimizer**: Boot health checks + warmup request guarantee cold start < 2s.
14. **Adaptive Performance Manager**: Dynamic resource scaling based on CPU/RAM load.
