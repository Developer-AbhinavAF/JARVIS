# Brain Layer & BrainAdapter Specification

## Overview
The Brain layer manages intent classification, model provider abstraction (`BrainAdapter`), profile selection, and reasoning extraction.

## BrainAdapter Provider Architecture
```
                     +----------------------+
                     |     Jarvis Core      |
                     +----------------------+
                                |
                                v
                     +----------------------+
                     |     BrainAdapter     |
                     +----------------------+
                                |
        +---------------+-------+-------+---------------+
        |               |               |               |
        v               v               v               v
  OllamaAdapter   GroqAdapter     GeminiAdapter   OpenAIAdapter
```
Supported providers: Ollama, Groq, OpenAI, Gemini, Anthropic, OpenRouter, LM Studio.

## Startup Warmup Routine
Immediately upon startup completion, `BrainAdapter` executes an async background ping request (`"hello"`) to ensure zero first-query latency penalty.
