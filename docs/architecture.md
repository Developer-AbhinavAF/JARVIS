# Execution-first architecture

```text
input
  -> SemanticIntentEngine
  -> Intent { intent, confidence, entities, context, level }
  -> confidence >= 0.95 and Level 0–2: execute or respond immediately
       -> ToolRegistry -> verified ToolResult -> natural response
  -> otherwise: lazy Reasoner/LLM fallback
```

`SessionContext` owns browser, website, folder, app, window, tab, selection, clipboard, screenshot, last tool/entity/person/command state. `MemoryStore` owns facts, conversation, mistakes, preferences, goals, relationships, projects, summaries, and `knowledge/` beneath the configured data root.

The LLM receives only `ToolSpec.llm_card()` objects: name, description, arguments, and example.
