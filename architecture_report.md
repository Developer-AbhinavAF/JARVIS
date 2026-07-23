# JARVIS Architecture Report

## Current Architecture Analysis

### Existing System
The current JARVIS implementation follows a pipeline approach but relies heavily on regex-based pattern matching:

```
User Input → Normalize → Regex Pattern Matching → Intent Classification → Entity Extraction (Regex) → Tool Selection → Execution → Response
```

### Problems Identified
1. **NLP System**: Heavily dependent on regex patterns and keyword matching
2. **Intent Classification**: Uses hardcoded patterns (e.g., `if "youtube" in text`)
3. **Entity Extraction**: Regex-based, limited flexibility
4. **Tool Selection**: Manual mapping, no semantic similarity
5. **Memory**: SQLite-based but missing JSON persistence requirements
6. **Knowledge**: Keyword-based search, no semantic understanding
7. **Context**: Basic history tracking, no pronoun resolution

## New Architecture Design

### Pipeline
```
User Input
↓
Fast Intent Router (LLM-based)
↓
Top-K Tool Selection (Semantic Similarity)
↓
LLM (Groq) with Fallback to Ollama
↓
Tool Call JSON Generation
↓
Execution Engine with Verification
↓
Response Generation
↓
Memory Store (JSON + SQLite)
```

### Components

#### 1. Intent Classification (LLM-based)
- **Input**: User text + conversation context
- **Process**: Use LLM to classify intent from predefined set
- **Output**: Intent label + confidence score
- **Fallback**: If confidence < threshold, ask for clarification

#### 2. Entity Extraction (LLM-based)
- **Input**: User text + intent
- **Process**: Extract structured entities using LLM
- **Output**: JSON with extracted entities
- **Example**: "open youtube and search interstellar" → `{intent: OPEN_WEB_APP, app: youtube, action: search, query: interstellar}`

#### 3. Top-K Tool Selection
- **Tool Metadata**: Pre-loaded on startup
- **Selection**: Semantic similarity between intent+entities and tool descriptions
- **Output**: Top K tools ranked by relevance

#### 4. Context Resolution
- **Pronouns**: Resolve "it", "this", "that", "there" to previous entities
- **History**: Maintain conversation context for resolution
- **Example**: "Open YouTube. Search there." → "Search YouTube"

#### 5. Memory System
- **memories.json**: User facts (name, age, dream, interests)
- **mistakes.json**: Learning from corrections
- **knowledge.json**: Document storage with semantic search
- **conversation_history.json**: Full conversation log

#### 6. Knowledge Base
- **Storage**: ChromaDB or FAISS for semantic search
- **Indexing**: Embeddings for all knowledge documents
- **Retrieval**: Semantic similarity search

#### 7. Execution Engine
- **Verification**: Every tool execution must be verified
- **Confirmation**: Destructive operations require user confirmation
- **Fallback**: Graceful degradation on failures

## Implementation Plan

### Phase 1: Core NLP Transformation
1. Replace regex-based intent classification with LLM-based
2. Implement LLM-based entity extraction
3. Add slot filling and context resolution
4. Implement Top-K tool selection

### Phase 2: Memory & Knowledge
1. Create JSON-based memory files
2. Implement mistake learning system
3. Add semantic search with ChromaDB/FAISS
4. Enhance conversation history tracking

### Phase 3: Enhanced Capabilities
1. Desktop control enhancements
2. System control with confirmation
3. File operations with safety checks
4. Media playback (Playwright/yt-dlp)
5. Speech improvements (ElevenLabs)
6. Ollama fallback refinement

### Phase 4: Testing & Validation
1. Run all 15 test cases
2. Generate reports
3. Fix any failures
4. Final validation

## Tool Categories

### Web Apps
- YouTube, Google, GitHub, Reddit, Instagram, Gmail, ChatGPT, Spotify

### Desktop Apps
- Chrome, Edge, VSCode, Notepad, Calculator, Paint, Camera

### System Control
- Sleep, Shutdown, Lock (with confirmation)

### Desktop Control
- Click, double-click, hover, type, paste, screenshot, screen analysis

### Media
- Play music/video via YouTube with Playwright/yt-dlp

### File Operations
- Create, read, rename, move (safe)
- Delete (requires confirmation)

## Language Support
- Primary: English
- Secondary: Hindi (transliteration support)
- Examples: "youtube kholo", "Mera naam kya hai"

## Success Criteria
1. No hardcoded responses
2. No keyword matching for intent
3. No fake/seeded memories
4. All tool executions verified
5. Destructive operations require confirmation
6. Semantic search for knowledge
7. Context resolution working
8. All 15 test cases passing
