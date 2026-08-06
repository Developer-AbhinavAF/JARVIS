# Execution-first memory report

`MemoryStore` persists `facts.json`, `conversation.json`, `mistakes.json`, `preferences.json`, `goals.json`, `relationships.json`, `projects.json`, `summaries.json`, and `knowledge/` under its data root. It loads them once into cache and performs vector cosine retrieval only when an embedding backend is available. It has no keyword fallback.

The default local n-gram vector backend keeps startup and retrieval local; a production semantic embedding backend can be injected through the `Embeddings` protocol.
