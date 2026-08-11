"""core/performance_manager.py — Performance & Resource Manager for JARVIS vNext++.

RESOURCE INDEPENDENCE (mandatory):
System-resource monitoring is an OPTIONAL diagnostic subsystem. It must
NEVER control the conversational AI:
- It is not part of prompt context, refusal logic, tool selection or
  response generation.
- adapt_parameters() no longer throttles LLM output based on CPU/RAM.
- check_system_load() remains available to diagnostics / explicit
  system-status tools only.
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
    """Adaptive resource monitoring and parameter scaling.

    Monitoring is isolated: the chat pipeline calls adapt_parameters(),
    which never consults system resources. Diagnostics may call
    check_system_load() independently.
    """

    def __init__(self):
        pass

    def check_system_load(self) -> Dict[str, Any]:
        """Inspect current CPU and RAM usage percentages (diagnostics only)."""
        if not PSUTIL_AVAILABLE:
            return {"cpu_percent": 0.0, "ram_percent": 0.0}
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        return {"cpu_percent": cpu, "ram_percent": ram}

    def adapt_parameters(self, max_tokens: int, top_k_rag: int) -> Tuple[int, int]:
        """Return parameters unchanged.

        The conversational AI must be fully independent from system load —
        a 400-word essay is always generated in full, at full token budget,
        regardless of CPU/RAM/GPU values.
        """
        return max_tokens, top_k_rag


performance_manager = PerformanceManager()