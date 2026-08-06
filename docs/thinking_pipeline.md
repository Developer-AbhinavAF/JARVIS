# Thinking Pipeline Specification

## Thought Leak Prevention
Reasoning block parsing occurs strictly inside `ThinkingMiddleware`. The raw `<think>...</think>` tags are never exposed to client interfaces.

## Stream Flow
```
Model Stream -> ThinkingMiddleware -> Event Bus -> Client UIs
                                        ├── ThinkingEvent (dimmed/faded UI display)
                                        └── FinalResponse (clean text tokens)
```
