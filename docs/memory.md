# Universal Memory System Specification

## Overview
Universal Memory provides semantic vector retrieval and direct key-value lookup across structured memory files.

## Memory Categories Layout
- `memory/facts.json`: User facts & attributes
- `memory/preferences.json`: Operational preferences & style
- `memory/goals.json`: Short/long-term goals
- `memory/projects.json`: Active project contexts
- `memory/relationships.json`: Contacts and entities
- `memory/mistakes.json`: Failure learnings & self-corrections
- `memory/patterns.json`: Learned workflow patterns
- `memory/conversation_history.json`: Compressed chat summaries
- `knowledge/`: Categorized document summaries

## Multi-Tier Memory Lookup
1. **Session Cache**: < 1 ms
2. **Recent Memory**: < 2 ms
3. **Exact Facts Store**: < 5 ms (Factual queries short-circuit vector search)
4. **Semantic Vector Search**: < 20 ms
5. **Archived Memory**: Background lookup
