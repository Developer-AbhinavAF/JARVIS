# JARVIS AI Router System

## Router Architecture

### Provider Priority
1. **QWEN3 (Ollama)** - Primary local model
2. **Groq** - Fast cloud API
3. **Other APIs** - Backup cloud providers
4. **Ollama Backup** - Additional local models

### Fallback Strategy
- Try providers in priority order
- Automatic failover on errors
- Health checking
- Latency monitoring
- Error recovery

## Primary Model: QWEN3

### Model Configuration
```
Model: QWEN3:1.7B Q4_K_M
Platform: Ollama (Local)
Quantization: Q4_K_M
Size: ~1GB RAM
Speed: Fast
Purpose: Primary inference
```

### Why QWEN3
- Excellent quality-to-size ratio
- Fast inference on consumer hardware
- Good multilingual support
- Strong reasoning capabilities
- Local execution (no network needed)

### Ollama Integration
```python
ollama_config = {
    "base_url": "http://localhost:11434",
    "model": "qwen2.5:1.7b",
    "timeout": 120,
    "stream": True,
    "options": {
        "temperature": 0.7,
        "top_p": 0.9,
        "num_ctx": 4096
    }
}
```

## Secondary Provider: Groq

### Groq Configuration
```python
groq_config = {
    "base_url": "https://api.groq.com/openai/v1",
    "models": [
        "llama-3.3-70b-versatile",
        "mixtral-8x7b-32768",
        "llama-3.1-8b-instant"
    ],
    "priority": 10,
    "timeout": 60
}
```

### Why Groq
- Extremely fast inference
- High-quality models
- Good free tier
- Low latency
- Reliable service

## Tertiary Providers

### OpenAI
```python
openai_config = {
    "base_url": "https://api.openai.com/v1",
    "models": ["gpt-4o", "gpt-4o-mini"],
    "priority": 50
}
```

### Anthropic
```python
anthropic_config = {
    "base_url": "https://api.anthropic.com/v1",
    "models": ["claude-3-5-sonnet-20241022"],
    "priority": 60
}
```

### OpenRouter
```python
openrouter_config = {
    "base_url": "https://openrouter.ai/api/v1",
    "models": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"],
    "priority": 70
}
```

## Backup Local Models

### Ollama Backup Models
```python
backup_models = [
    "llama3.2:latest",
    "mistral:latest",
    "phi3:latest",
    "gemma2:latest"
]
```

### When to Use Backups
- Primary model unavailable
- Primary model too slow
- Specialized task needs
- Model comparison
- Testing purposes

## Router Logic

### Provider Selection
```python
def select_provider(task):
    # Try QWEN3 first
    if ollama_available("qwen2.5:1.7b"):
        return "ollama"
    
    # Try Groq
    if groq_available():
        return "groq"
    
    # Try other APIs
    for provider in api_providers:
        if provider_available(provider):
            return provider
    
    # Try backup Ollama models
    for model in backup_models:
        if ollama_available(model):
            return "ollama"
    
    # All failed
    return None
```

### Health Checking
```python
def check_provider_health(provider):
    # Check availability
    # Measure latency
    # Check error rate
    # Validate response quality
    # Update provider status
```

### Fallback Logic
```python
def execute_with_fallback(prompt):
    for provider in providers:
        try:
            response = call_provider(provider, prompt)
            if validate_response(response):
                return response
        except Exception as e:
            log_error(provider, e)
            continue
    return "All providers failed"
```

## Streaming Support

### Real-Time Streaming
- Stream tokens as they arrive
- No waiting for complete response
- Show thinking process
- Interactive experience
- Natural conversation flow

### Streaming Implementation
```python
async def stream_response(provider, messages):
    async for token in provider.chat_stream(messages):
        yield token
        # Update UI in real-time
```

## Thinking Mode

### Thinking API
- Use Ollama thinking API
- Show thinking tokens
- Display reasoning process
- Chain-of-thought display
- Real-time thought updates

### Thinking Display
```
Thinking...
- Understanding user intent
- Analyzing context
- Selecting tools
- Planning execution

Answer...
```

## Model Specialization

### Task Routing
- Simple tasks → Fast models
- Complex reasoning → Large models
- Creative tasks → Creative models
- Code tasks → Code models
- Multilingual → Multilingual models

### Smart Routing
```python
def route_by_task(task):
    if task.type == "simple":
        return fast_model
    elif task.type == "complex":
        return large_model
    elif task.type == "creative":
        return creative_model
    else:
        return default_model
```

## Performance Monitoring

### Metrics
- Response time
- Token generation speed
- Error rate
- Provider uptime
- Cost tracking

### Optimization
- Prefer fastest healthy provider
- Cache responses when appropriate
- Batch requests
- Use streaming for long responses
- Optimize prompts

## Cost Management

### Cost Tracking
- Track API costs
- Monitor token usage
- Set cost limits
- Alert on thresholds
- Optimize for cost

### Free Tier Optimization
- Prefer free providers
- Use local models when possible
- Minimize token usage
- Cache responses
- Efficient prompting

## Reliability Features

### Retry Logic
- Automatic retry on transient errors
- Exponential backoff
- Max retry limits
- Different provider on retry
- Error classification

### Degradation
- Graceful degradation
- Fallback to simpler models
- Offline mode support
- Cached responses
- Error recovery

## Configuration

### Environment Variables
```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.7b

# Groq
GROQ_API_KEY=your_key
GROQ_BASE_URL=https://api.groq.com/openai/v1

# OpenAI
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic
ANTHROPIC_API_KEY=your_key
ANTHROPIC_BASE_URL=https://api.anthropic.com/v1

# OpenRouter
OPENROUTER_API_KEY=your_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### Provider Configuration
```python
router_config = {
    "primary": "ollama",
    "secondary": "groq",
    "fallback": ["openai", "anthropic", "openrouter"],
    "local_fallback": ["llama3.2", "mistral", "phi3"],
    "health_check_interval": 60,
    "max_retries": 3,
    "timeout": 120
}
```