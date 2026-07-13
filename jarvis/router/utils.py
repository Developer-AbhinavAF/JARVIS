from __future__ import annotations

import json
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)


def safe_json_loads(text: str, default: Any = None) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


def truncate_text(text: str, max_chars: int = 200) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def normalize_model_name(model: str) -> str:
    return model.lower().replace(" ", "-").replace("_", "-")


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def now_ms() -> float:
    return time.time() * 1000


class Timer:
    def __init__(self) -> None:
        self._marks: dict[str, float] = {}

    def mark(self, label: str) -> None:
        self._marks[label] = time.time()

    def elapsed(self, label: str) -> float:
        start = self._marks.get(label, time.time())
        return (time.time() - start) * 1000

    def report(self) -> str:
        if not self._marks:
            return ""
        total = sum(self.elapsed(k) for k in self._marks)
        parts = " | ".join(f"{k}:{self.elapsed(k):.0f}ms" for k in self._marks)
        return f"[TIMING] {parts} | TOTAL:{total:.0f}ms"

    def reset(self) -> None:
        self._marks.clear()
