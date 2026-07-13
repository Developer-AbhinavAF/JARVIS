from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

from .models import ChatRequest
from .interfaces import BaseProvider

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    provider: str
    model: str
    latency_ms: float
    tokens_per_sec: float
    success: bool
    error: str = ""


class Benchmark:
    """Benchmarks provider performance for auto-learning."""

    TEST_PROMPTS = [
        "What is the capital of France?",
        "Explain quantum computing in simple terms.",
        "Write a Python function to merge two sorted lists.",
        "Summarize: The Industrial Revolution was a period of major industrialization.",
    ]

    def __init__(self) -> None:
        self._results: dict[str, list[BenchmarkResult]] = {}

    def run_provider(
        self,
        provider: BaseProvider,
        model: str | None = None,
        num_tests: int = 2,
    ) -> list[BenchmarkResult]:
        results: list[BenchmarkResult] = []
        prompts = self.TEST_PROMPTS[:num_tests]

        for prompt in prompts:
            request = ChatRequest(
                messages=[{"role": "user", "content": prompt}],
                model=model or next(iter(provider._known_models), None),
                max_tokens=50,
                temperature=0.1,
            )

            start = time.time()
            try:
                response = provider.chat(request)
                latency = (time.time() - start) * 1000
                tokens = response.tokens_used or len(prompt) // 4
                tokens_per_sec = (tokens / latency) * 1000 if latency > 0 else 0
                result = BenchmarkResult(
                    provider=provider.name,
                    model=response.model,
                    latency_ms=latency,
                    tokens_per_sec=tokens_per_sec,
                    success=True,
                )
            except Exception as exc:
                latency = (time.time() - start) * 1000
                result = BenchmarkResult(
                    provider=provider.name,
                    model=str(model),
                    latency_ms=latency,
                    tokens_per_sec=0,
                    success=False,
                    error=str(exc),
                )

            results.append(result)

        self._results[provider.name] = results
        return results

    def benchmark_all(
        self,
        providers: list[BaseProvider],
    ) -> dict[str, list[BenchmarkResult]]:
        results: dict[str, list[BenchmarkResult]] = {}
        for provider in providers:
            try:
                results[provider.name] = self.run_provider(provider)
            except Exception as exc:
                logger.warning("Benchmark failed for %s: %s", provider.name, exc)
        return results

    def get_best_provider(self, metric: str = "latency") -> str | None:
        best_name = None
        best_value = float("inf") if metric == "latency" else 0.0

        for name, results in self._results.items():
            if not results:
                continue
            avg_latency = sum(r.latency_ms for r in results if r.success) / max(sum(1 for r in results if r.success), 1)
            avg_tps = sum(r.tokens_per_sec for r in results if r.success) / max(sum(1 for r in results if r.success), 1)

            if metric == "latency" and avg_latency < best_value:
                best_value = avg_latency
                best_name = name
            elif metric == "speed" and avg_tps > best_value:
                best_value = avg_tps
                best_name = name

        return best_name
