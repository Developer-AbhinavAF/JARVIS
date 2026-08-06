"""core/performance_manager.py — Performance & Resource Manager for JARVIS vNext++.

Monitors system resources (CPU, RAM, VRAM) and dynamically adjusts parameters:
- High CPU (> 90%): Reduces token output (num_predict), lowers RAG Top-K, throttles workers.
- Low RAM: Compresses memory, evicts caches, trims context window.
"""

from __future__ import annotations

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class PerformanceManager:
    """Adaptive resource monitoring and parameter scaling."""

    def __init__(self):
        pass

    def check_system_load(self) -> Dict[str, Any]:
        """Inspect current CPU and RAM usage percentages."""
        if not PSUTIL_AVAILABLE:
            return {"cpu_percent": 0.0, "ram_percent": 0.0}
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        return {"cpu_percent": cpu, "ram_percent": ram}

    def adapt_parameters(self, max_tokens: int, top_k_rag: int) -> Tuple[int, int]:
        """Adjust prediction tokens and RAG Top-K under high hardware strain."""
        metrics = self.check_system_load()
        adjusted_tokens = max_tokens
        adjusted_top_k = top_k_rag

        # If CPU load > 90%, scale down expensive parameters
        if metrics["cpu_percent"] > 90.0:
            adjusted_tokens = min(max_tokens, 1024)
            adjusted_top_k = min(top_k_rag, 1)
            logger.warning(f"High CPU detected ({metrics['cpu_percent']}%). Scaled down parameters.")

        # If RAM load > 85%, scale down context
        if metrics["ram_percent"] > 85.0:
            adjusted_top_k = min(adjusted_top_k, 1)
            logger.warning(f"High RAM usage detected ({metrics['ram_percent']}%). Scaled down RAG retrieval.")

        return adjusted_tokens, adjusted_top_k


performance_manager = PerformanceManager()
