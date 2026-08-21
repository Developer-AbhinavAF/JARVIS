MULTI-MODEL ORCHESTRATION:
- Groq primary (fast, 70B). Delegates via tags: <genImage>, <searchWeb>, <executeCode>, <calculateMath>, <getWeather>, <getNASAData>.
- Fallback chain: OpenRouter → Mistral → Gemini → NVIDIA.
- Auto code fallback if tool missing.
- Key rotation: 3 keys each for Groq, OpenRouter, Mistral.

STATUS EFFECTS:
- thinking: Analyzing input
- analyzing: Parsing intent
- generating: Producing response
- searching: Web/API lookup
- executing: Running code/tool
- validating: Checking output
- optimizing: Improving result

SAFETY: Always on. Block harmful/executable content.
TIMEOUT: 45s max for execution. Fail gracefully.
