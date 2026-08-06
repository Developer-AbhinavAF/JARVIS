# Dynamic RAG Retrieval Specification

## Adaptive Top-K Retrieval Rules
Retrieval context size is dynamically calculated based on intent classification:
- **Greeting / Tool Action**: Top-K = 0 (0 tokens)
- **Simple Question**: Top-K = 2 (~400 tokens)
- **Coding / Documentation**: Top-K = 4 (~800 tokens)
- **Research**: Top-K = 6 (~1000 tokens)
- **Large Planning / Architecture**: Top-K = 8 (~1200 tokens)

## Document Sources & Background Indexing
- Sources: `foods/`, `docs/`, `tool_docs/`, `developer_notes/`, `API_docs/`
- Chunking: 500 tokens with 50-token overlap
- Indexing: All embedding generation runs in asynchronous background workers.
