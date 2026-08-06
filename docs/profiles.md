# Adaptive Brain Profiles Specification

## Profile Parameters

| Profile | Purpose | Think | Temperature | Num Predict |
|---|---|---|---|---|
| `FAST_PROFILE` | Greetings, simple chat, tools, facts | `false` | 0.20 | 128 |
| `NORMAL_PROFILE` | General conversation, basic Q&A | `false` | 0.30 | 512 |
| `MEMORY_PROFILE` | Fact lookup, conversation recall | `false` | 0.10 | 256 |
| `WRITING_PROFILE` | Essays, notes, documentation | `true` | 0.50 | 4096 |
| `CODING_PROFILE` | Code generation, architecture, debug | `true` | 0.20 | 4096 |
| `RESEARCH_PROFILE` | Synthesis, deep comparisons | `true` | 0.40 | 4096 |
