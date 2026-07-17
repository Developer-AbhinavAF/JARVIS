"""Benchmarking — Tracks performance metrics across all subsystems.

NLP latency, vision speed, speech latency, tool speed, router performance.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkEntry:
    """Single benchmark measurement."""
    timestamp: float = 0.0
    subsystem: str = ""
    operation: str = ""
    latency_ms: float = 0.0
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class Benchmarking:
    """Tracks performance benchmarks for all subsystems.

    Usage:
        bench = Benchmarking()
        bench.record("nlp", "process", 45.0)
        bench.record("router", "select", 5.0)
        stats = bench.get_subsystem("nlp")
    """

    def __init__(self, max_entries: int = 10000):
        self._entries: list[BenchmarkEntry] = []
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._active: dict[str, float] = {}  # operation start times

    def start(self, subsystem: str, operation: str = ""):
        key = f"{subsystem}:{operation}"
        self._active[key] = time.time()

    def end(self, subsystem: str, operation: str = "", success: bool = True) -> float:
        key = f"{subsystem}:{operation}"
        start = self._active.pop(key, 0)
        if start == 0:
            return 0.0
        latency = (time.time() - start) * 1000
        self.record(subsystem, operation, latency, success)
        return latency

    def record(self, subsystem: str, operation: str, latency_ms: float, success: bool = True):
        entry = BenchmarkEntry(
            timestamp=time.time(),
            subsystem=subsystem,
            operation=operation,
            latency_ms=latency_ms,
            success=success,
        )
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

    def get_subsystem(self, subsystem: str, limit: int = 100) -> dict[str, Any]:
        with self._lock:
            entries = [e for e in self._entries if e.subsystem == subsystem][-limit:]
        if not entries:
            return {"subsystem": subsystem, "samples": 0}
        latencies = [e.latency_ms for e in entries]
        successes = sum(1 for e in entries if e.success)
        return {
            "subsystem": subsystem,
            "samples": len(entries),
            "avg_ms": round(sum(latencies) / len(latencies), 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
            "p50_ms": round(sorted(latencies)[len(latencies) // 2], 2) if latencies else 0,
            "success_rate": round(successes / len(entries), 3),
        }

    def get_all(self) -> dict[str, Any]:
        subsystems = set()
        with self._lock:
            for e in self._entries:
                subsystems.add(e.subsystem)
        return {s: self.get_subsystem(s) for s in subsystems}

    def get_total_entries(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self):
        with self._lock:
            self._entries.clear()

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            entries = list(self._entries)
        subsystems = set(e.subsystem for e in entries)
        return {
            "total_entries": len(entries),
            "subsystems": len(subsystems),
        }


# Global instance
benchmarking = Benchmarking()

__all__ = ["Benchmarking", "BenchmarkEntry", "benchmarking"]
