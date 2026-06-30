# JARVIS Production Personal AI OS Architecture

## Audit Summary

JARVIS already has useful building blocks: a Python assistant core, an Ollama-compatible LLM service, SQLite memory, command handlers, desktop FastAPI routes, Electron/Vite UI, document readers, YouTube learning, and early NLP/reflection modules.

The current bottlenecks are architectural rather than conceptual:

- `jarvis/main.py` and `jarvis-desktop/backend/app.py` contain large monolithic command/API paths.
- Tool definitions are plain callables, so routing, permissions, monitoring, schemas, and analytics cannot scale cleanly to 1000+ tools.
- Several heavy dependencies are imported eagerly in backend paths, increasing startup time and RAM pressure.
- Memory is split across SQLite tables, Chroma fallback, notes, YouTube notes, and ad hoc conversation history without one normalized dashboard/search/edit/delete contract.
- RAG is not consistently applied before LLM responses.
- API integrations are duplicated and not uniformly cached, timed out, or key-gated.

## Target Runtime Principle

`Tool > Memory > RAG > LLM`

Every request should pass through this order:

1. Deterministic NLP intent and entity extraction.
2. Tool router for high-confidence direct actions.
3. Memory lookup or memory write when the user asks about stored knowledge.
4. RAG context builder for relevant conversation, learning, project, research, and document context.
5. LLM fallback only after the cheaper, more accurate layers have been attempted.

## Implemented Foundation

- `jarvis/api_services.py`: dedicated lazy services for Tavily, OpenRouter, Gemini, OpenWeather, NewsAPI, Alpha Vantage, YouTube, ElevenLabs, SerpAPI, Resend, TMDB, NASA, Finnhub, API Ninjas, and Calendarific.
- `jarvis/tool_system.py`: typed tool registry, router, executor, permissions, caching, timeout handling, and SQLite analytics.
- `jarvis/memory_os.py`: unified SQLite memory with required fields, FTS search when available, memory editing/deletion, conversation turns, and knowledge graph edges.
- `jarvis/rag.py`: compact context builder that searches OS memory, learning memory, conversations, and notes under a strict character budget.
- `jarvis/agents.py`: planner, tool, research, memory, learning, document, coding, finance, NASA, and orchestrator agent specs.
- `jarvis/personal_os.py`: orchestration layer that enforces Tool > Memory > RAG > LLM.
- `jarvis/api_routes.py`: backend bridge exposing `/api/os/*` routes without rewriting the existing backend.

## Database Design

Primary database: `data/jarvis_os.db`

Core tables:

- `os_memories`: `id`, `category`, `importance`, `timestamp`, `source`, `tags`, `summary`, `content`, `metadata`.
- `os_memories_fts`: optional FTS5 index for fast local search.
- `conversation_turns`: raw chat turns by session.
- `knowledge_edges`: graph edges between memory records with relation and weight.

Existing databases remain usable:

- `data/memory.db`: legacy todos, notes, reminders, preferences, conversations.
- `data/learning_memory_fallback.db`: fallback learning memory.
- `data/chroma`: optional Chroma persistent vector store.
- `data/tool_analytics.db`: tool monitoring and performance analytics.

## Service Design

Services are lazy and key-gated. Missing keys return structured errors instead of crashing startup.

Service classes:

- `TavilyService`: research search.
- `OpenRouterService`: cloud model fallback.
- `GeminiService`: Gemini fallback.
- `OpenWeatherService`: weather.
- `NewsAPIService`: news.
- `AlphaVantageService`: market quotes.
- `YouTubeService`: YouTube search.
- `ElevenLabsService`: voice generation.
- `SerpAPIService`: Google-style search.
- `ResendService`: email sending.
- `TMDBService`: media/movie search.
- `NASAService`: APOD and NEO data.
- `FinnhubService`: finance quotes/company data.
- `APINinjasService`: facts, sentiment, utility APIs.
- `CalendarificService`: holidays.

## Tool Architecture

Tool records include:

- name
- description
- category
- callable handler
- permissions
- parameter schema
- aliases
- enabled flag
- timeout
- cache TTL
- confirmation requirement

The registry can wrap the existing `jarvis.tools.TOOL_REGISTRY` while also supporting future typed tools. The executor adds timeout isolation, permissions, optional caching, and durable analytics.

## Agent Architecture

Agents are lightweight routing profiles rather than always-running processes. This keeps RAM low.

- Planner Agent
- Tool Agent
- Research Agent
- Memory Agent
- Learning Agent
- Document Agent
- Coding Agent
- Finance Agent
- NASA Agent
- Orchestrator Agent

The orchestrator selects the best profile from intent and keywords, then constrains tool and memory categories for that request.

## RAG Architecture

Fast path:

1. Search unified OS memory with FTS/LIKE.
2. Search learning memory, using Chroma when available and SQLite fallback otherwise.
3. Search legacy conversations and notes.
4. Deduplicate and rank by importance.
5. Pack only the most useful snippets into `RAG_CONTEXT_MAX_CHARS`.

This avoids huge prompts and keeps Llama 3.2 3B responsive.

## Dashboard Design

The production dashboard should expose:

- Memory dashboard: categories, recent memories, edit/delete/search.
- Tool dashboard: tool count, enabled/disabled state, permission class, latency, error rate.
- RAG dashboard: retrieved items and context size.
- API dashboard: key configured/unconfigured status and last errors.
- Learning dashboard: sources ingested, chunk counts, summaries, embeddings status.
- Project dashboard: repo memory, recent files, architecture notes.
- Finance/NASA dashboards: domain-specific watchlists and saved research.

The backend now exposes the first production endpoints under `/api/os/*`.

## Roadmap

Phase 1, core spine:

- Unified memory store.
- Tool registry/router/executor.
- API service layer.
- RAG context builder.
- Personal AI OS orchestrator.
- Backend `/api/os/*` bridge.

Phase 2, learning pipeline:

- Normalize source ingestion for YouTube, PDF, DOCX, TXT, Markdown, websites, notes, papers, and corrections.
- Add chunking, summary, embedding cache, and Chroma upsert using the same `OSMemory` metadata.
- Add source quality scoring and citation metadata.

Phase 3, research:

- Multi-source search planner.
- Fact verification.
- Source ranking.
- Research reports with citations.
- Academic paper extraction and note generation.

Phase 4, documents and coding:

- PDF/DOCX/TXT/Markdown chat through the common RAG layer.
- Document comparison and editing.
- Repository index, code search, architecture review, bug detection, and multi-file editing.

Phase 5, dashboards:

- Replace placeholder desktop widgets with real `/api/os/*` data.
- Memory editing/deletion UI.
- Tool analytics UI.
- Learning and research dashboards.

## Feature Priority by Value

Highest value:

- Memory search/edit/delete.
- Tool router/executor.
- RAG before LLM.
- Document chat.
- Web research with verification.
- Repository/code intelligence.
- Daily review and task manager.

Medium value:

- YouTube learning.
- Finance/NASA dashboards.
- Visual OCR and screenshot analysis.
- Research report generation.

Lower initial value:

- Large numbers of entertainment/media endpoints.
- Placeholder smart-home integrations.
- Always-on multi-agent workers.

## Feature Priority by Performance Cost

Lowest cost:

- SQLite memory.
- Deterministic NLP.
- Tool routing.
- API wrappers.
- Cached web/API calls.

Medium cost:

- Chroma retrieval.
- Document parsing.
- YouTube transcript processing.
- Code indexing.

Highest cost:

- Local vision models.
- OCR on large images.
- Browser automation.
- Always-on agents.
- Long LLM reflections.

## Recommended File Structure

```text
jarvis/
  api_services.py
  tool_system.py
  memory_os.py
  rag.py
  agents.py
  personal_os.py
  api_routes.py
  learning/
    ingestion.py
    chunking.py
    embeddings.py
  research/
    planner.py
    verifier.py
    reports.py
  documents/
    readers.py
    comparison.py
  coding/
    repo_index.py
    code_search.py
  dashboards/
    schemas.py
```

The current implementation starts the production spine without forcing an immediate full repo reshuffle.
