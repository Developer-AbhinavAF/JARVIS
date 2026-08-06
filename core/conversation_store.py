"""conversation_store — Persist every turn to convo/ as JSON.

The convo directory is the single source of truth for the ongoing
conversation: on every fallback (start_model -> backup1..3 -> cloud APIs)
the brain re-reads it, so switching backends never loses context.
"""

from __future__ import annotations

import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

CONVO_DIR = Path(__file__).resolve().parent.parent / "convo"
CONVO_FILE = CONVO_DIR / "conversations.json"
MAX_TURNS = 200


class ConversationStore:
    """Append user/assistant turns and reload them as chat messages."""

    def __init__(self, path: Path = CONVO_FILE) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._turns: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._turns, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            logger.debug("Could not persist conversation: %s", e)

    def append(self, user: str, assistant: str, provider: str = "", model: str = "", tier: str = "") -> None:
        """Record one turn (user query + LLM response)."""
        self._turns.append({
            "timestamp": round(time.time(), 2),
            "user": user,
            "assistant": assistant,
            "provider": provider,
            "model": model,
            "tier": tier,
        })
        if len(self._turns) > MAX_TURNS:
            self._turns = self._turns[-MAX_TURNS:]
        self._save()

    def messages(self, limit: int = 20) -> List[Dict[str, str]]:
        """Chat-format history to feed any provider on (re)start or fallback."""
        messages: List[Dict[str, str]] = []
        for turn in self._turns[-limit:]:
            if turn.get("user"):
                messages.append({"role": "user", "content": turn["user"]})
            if turn.get("assistant"):
                messages.append({"role": "assistant", "content": turn["assistant"]})
        return messages

    def last_turns(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self._turns[-limit:]

    def clear(self) -> None:
        self._turns = []
        self._save()


conversation_store = ConversationStore()
