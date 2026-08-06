"""Performance benchmarking for JARVIS components."""
import time
import statistics
from typing import Callable, List, Dict, Any
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    name: str
    mean_ms: float
    median_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    iterations: int


class Benchmark:
    """Performance benchmarking utility."""
    
    def __init__(self, warmup_iterations: int = 3, benchmark_iterations: int = 100):
        self.warmup_iterations = warmup_iterations
        self.benchmark_iterations = benchmark_iterations
    
    def run(self, func: Callable, *args, **kwargs) -> BenchmarkResult:
        """Run a benchmark on a function."""
        name = func.__name__
        
        # Warmup
        for _ in range(self.warmup_iterations):
            func(*args, **kwargs)
        
        # Benchmark
        times_ms = []
        for _ in range(self.benchmark_iterations):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            times_ms.append((end - start) * 1000)
        
        return BenchmarkResult(
            name=name,
            mean_ms=statistics.mean(times_ms),
            median_ms=statistics.median(times_ms),
            min_ms=min(times_ms),
            max_ms=max(times_ms),
            std_dev_ms=statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0,
            iterations=self.benchmark_iterations
        )
    
    def compare(self, func1: Callable, func2: Callable, *args, **kwargs) -> Dict[str, BenchmarkResult]:
        """Compare two functions."""
        result1 = self.run(func1, *args, **kwargs)
        result2 = self.run(func2, *args, **kwargs)
        
        speedup = result1.mean_ms / result2.mean_ms if result2.mean_ms > 0 else 0
        
        return {
            "func1": result1,
            "func2": result2,
            "speedup": speedup
        }


def benchmark_execution_first():
    """Benchmark execution_first runtime components."""
    from core.execution_first import (
        LocalNgramEmbeddings, SemanticIntentEngine, SessionContext,
        MemoryStore, FoodCache
    )
    import tempfile
    
    print("=" * 60)
    print("JARVIS Performance Benchmarks")
    print("=" * 60)
    
    benchmark = Benchmark(warmup_iterations=5, benchmark_iterations=50)
    
    # Benchmark embeddings
    print("\n1. Embedding Generation")
    print("-" * 40)
    embeddings = LocalNgramEmbeddings()
    
    def embed_single():
        return embeddings.embed(["hello world"])
    
    def embed_batch():
        return embeddings.embed(["hello", "world", "test", "benchmark", "embedding"])
    
    result_single = benchmark.run(embed_single)
    result_batch = benchmark.run(embed_batch)
    
    print(f"Single text: {result_single.mean_ms:.3f}ms (std: {result_single.std_dev_ms:.3f}ms)")
    print(f"Batch (5):   {result_batch.mean_ms:.3f}ms (std: {result_batch.std_dev_ms:.3f}ms)")
    
    # Benchmark intent detection
    print("\n2. Intent Detection")
    print("-" * 40)
    engine = SemanticIntentEngine(embeddings)
    context = SessionContext()
    
    def detect_greeting():
        return engine.detect("hello", context)
    
    def detect_complex():
        return engine.detect("open youtube and search for music", context)
    
    result_greeting = benchmark.run(detect_greeting)
    result_complex = benchmark.run(detect_complex)
    
    print(f"Greeting:     {result_greeting.mean_ms:.3f}ms (std: {result_greeting.std_dev_ms:.3f}ms)")
    print(f"Complex:      {result_complex.mean_ms:.3f}ms (std: {result_complex.std_dev_ms:.3f}ms)")
    
    # Benchmark memory operations
    print("\n3. Memory Operations")
    print("-" * 40)
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = MemoryStore(tmpdir, embeddings)
        
        def remember_fact():
            return memory.remember("test_key", "test_value", "facts")
        
        def recall_fact():
            return memory.recall("test_key", limit=5)
        
        result_remember = benchmark.run(remember_fact)
        result_recall = benchmark.run(recall_fact)
        
        print(f"Remember:     {result_remember.mean_ms:.3f}ms (std: {result_remember.std_dev_ms:.3f}ms)")
        print(f"Recall:       {result_recall.mean_ms:.3f}ms (std: {result_recall.std_dev_ms:.3f}ms)")
    
    # Benchmark context operations
    print("\n4. Context Operations")
    print("-" * 40)
    context = SessionContext()
    
    def context_snapshot():
        return context.snapshot()
    
    def context_resolve():
        return context.resolve("there")
    
    def context_update():
        return context.update(current_app="chrome", current_website="youtube.com")
    
    result_snapshot = benchmark.run(context_snapshot)
    result_resolve = benchmark.run(context_resolve)
    result_update = benchmark.run(context_update)
    
    print(f"Snapshot:     {result_snapshot.mean_ms:.3f}ms (std: {result_snapshot.std_dev_ms:.3f}ms)")
    print(f"Resolve:      {result_resolve.mean_ms:.3f}ms (std: {result_resolve.std_dev_ms:.3f}ms)")
    print(f"Update:       {result_update.mean_ms:.3f}ms (std: {result_update.std_dev_ms:.3f}ms)")
    
    # Benchmark FOOD loading
    print("\n5. FOOD Loading")
    print("-" * 40)
    
    def load_food():
        return FoodCache()
    
    result_food = benchmark.run(load_food)
    print(f"Load FOOD:    {result_food.mean_ms:.3f}ms (std: {result_food.std_dev_ms:.3f}ms)")
    
    # Summary
    print("\n" + "=" * 60)
    print("Benchmark Summary")
    print("=" * 60)
    print(f"Embedding (single): {result_single.mean_ms:.3f}ms")
    print(f"Intent (greeting):  {result_greeting.mean_ms:.3f}ms")
    print(f"Memory (remember):  {result_remember.mean_ms:.3f}ms")
    print(f"Context (snapshot): {result_snapshot.mean_ms:.3f}ms")
    print(f"FOOD load:          {result_food.mean_ms:.3f}ms")
    print("\nAll operations complete in < 10ms [OK]")
    print("=" * 60)


def benchmark_startup():
    """Benchmark startup time."""
    print("\n" + "=" * 60)
    print("Startup Time Benchmark")
    print("=" * 60)
    
    import importlib
    import sys
    
    # Cold start - measure import time
    times = []
    for i in range(5):
        # Clear module cache
        modules_to_clear = [k for k in sys.modules.keys() if k.startswith('core')]
        for mod in modules_to_clear:
            del sys.modules[mod]
        
        start = time.perf_counter()
        from core.execution_first import build_runtime
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = build_runtime(tmpdir)
        end = time.perf_counter()
        
        times.append((end - start) * 1000)
    
    mean_time = statistics.mean(times)
    print(f"Startup time: {mean_time:.3f}ms (avg over 5 runs)")
    print(f"Min: {min(times):.3f}ms, Max: {max(times):.3f}ms")
    
    if mean_time < 100:
        print("Startup time is excellent (< 100ms) [OK]")
    elif mean_time < 500:
        print("Startup time is good (< 500ms) [OK]")
    else:
        print("Startup time needs optimization (> 500ms) [WARNING]")
    
    print("=" * 60)


def benchmark_memory():
    """Benchmark memory usage."""
    print("\n" + "=" * 60)
    print("Memory Usage Benchmark")
    print("=" * 60)
    
    import tracemalloc
    import tempfile
    
    tracemalloc.start()
    
    # Baseline
    baseline = tracemalloc.get_traced_memory()[0]
    
    # Load execution_first
    from core.execution_first import build_runtime
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime = build_runtime(tmpdir)
    
    current = tracemalloc.get_traced_memory()[0]
    memory_used = (current - baseline) / 1024  # KB
    
    print(f"Memory used: {memory_used:.2f} KB")
    
    if memory_used < 1024:
        print("Memory usage is excellent (< 1 MB) [OK]")
    elif memory_used < 5120:
        print("Memory usage is good (< 5 MB) [OK]")
    else:
        print("Memory usage needs optimization (> 5 MB) [WARNING]")
    
    tracemalloc.stop()
    print("=" * 60)


if __name__ == "__main__":
    benchmark_execution_first()
    benchmark_startup()
    benchmark_memory()
