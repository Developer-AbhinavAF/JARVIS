# Performance & Adaptive Resource Manager Specification

## Latency Goals (Host: Intel i5 6th Gen, 8GB RAM, CPU-Only)
- **Cold Start (Post Warmup)**: < 2.0 s
- **Simple Response Latency**: < 300 ms
- **Tool Execution Start**: < 100 ms
- **Facts Lookup**: < 5 ms
- **Context Resolution**: < 10 ms
- **Memory Search**: < 20 ms
- **Prompt Assembly**: < 20 ms

## Adaptive Resource Scaling
- **CPU > 90%**: Reduce `num_predict`, decrease retrieval Top-K, throttle background workers.
- **Low RAM**: Compress memory, evict LRU cache, trim context window.
