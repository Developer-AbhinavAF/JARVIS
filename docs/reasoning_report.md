# Reasoning report

| Level | Route | Budget |
|---:|---|---|
| 0 | Local reply | zero reasoning |
| 1 | Tool execution | no LLM reasoning |
| 2 | Memory operation | bounded local retrieval |
| 3 | Lazy reasoner | normal reasoning |
| 4 | Lazy reasoner | complex reasoning |

The stopping rule is structural: successful high-confidence dispatch returns immediately and has no subsequent planning/reconsideration call.
