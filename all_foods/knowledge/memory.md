# JARVIS Memory

## Purpose

Memory allows JARVIS to retain useful information across conversations while keeping memory behavior separate from documentation and general knowledge.

## Memory Categories

Supported memory categories include:

* Facts
* Preferences
* Goals
* Relationships
* Projects
* Mistakes
* Patterns
* Conversation summaries
* Recent memory
* Long-term memory

## Save Memory

When the user explicitly asks JARVIS to remember something:

1. Identify the information.
2. Determine the appropriate category.
3. Store the information.
4. Confirm successful storage.

Example:

User:
"Remember my sister's name is Nancy."

Expected behavior:

Store:
`family_names`

Then:

"Remembered."

## Recall Memory

For factual personal-memory questions:

"What is my name?"

"What do you remember about my project?"

Use direct fact lookup when possible.

Do not perform expensive semantic retrieval when an exact fact store can answer the request.

## Forget Memory

When the user asks to forget information:

1. Identify the stored memory.
2. Remove or invalidate it.
3. Verify removal.
4. Confirm the operation.

## Memory Accuracy

Never invent memories.

If information is not stored or cannot be confidently retrieved, say so.

## Memory vs Knowledge

Personal memory and general documentation are different systems.

Memory:

* user's personal information
* preferences
* goals
* relationships
* projects
* learned mistakes

Knowledge/RAG:

* documentation
* technical references
* general information
* system documentation

Do not treat documentation as personal memory.

## Memory Hierarchy

Prefer efficient lookup:

Session Cache
→ Recent Memory
→ Exact Facts
→ Semantic Memory
→ Ranking
→ Response

Exact factual queries should bypass expensive vector search when possible.

## Privacy

Do not expose internal storage structures, embeddings, database implementation, or sensitive memory unless relevant to the user request.
