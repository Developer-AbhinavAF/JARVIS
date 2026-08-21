"""conversation_store — Persist every turn to convo/ as JSON.

The convo directory is the single source of truth for the ongoing
conversation: on every fallback (start_model -> backup1..3 -> cloud APIs)
the brain re-reads it, so switching backends never loses context.

Supports isolated sessions for n8n integration to prevent automated
queries from polluting the user's personal conversation history.
"""

from __future__ import annotations

import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONVO_DIR = Path(__file__).resolve().parent.parent / "convo"
CONVO_FILE = CONVO_DIR / "conversations.json"
MAX_TURNS = 200

# Session IDs that should use isolated storage (n8n integration)
N8N_SESSION_PREFIXES = ("n8n-", "n8n_")


class ConversationStore:
    """Append user/assistant turns and reload them as chat messages.
    
    Supports session-based isolation for automated/n8n sessions.
    """

    def __init__(self, path: Path = CONVO_FILE) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._turns: List[Dict[str, Any]] = self._load()
        # Isolated session stores (for n8n and other automated sessions)
        self._isolated_sessions: Dict[str, List[Dict[str, Any]]] = {}

    def _is_isolated_session(self, session_id: str) -> bool:
        """Check if session should be isolated from main conversation."""
        if not session_id:
            return False
        return any(session_id.startswith(prefix) for prefix in N8N_SESSION_PREFIXES)

    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a specific session."""
        safe_id = session_id.replace("/", "_").replace("\\", "_")
        return CONVO_DIR / f"conversations_{safe_id}.json"

    def _load(self, path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Load turns from a specific path or default."""
        load_path = path if path else self._path
        try:
            return json.loads(load_path.read_text(encoding="utf-8")) if load_path.exists() else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, path: Optional[Path] = None) -> None:
        """Save turns to a specific path or default."""
        save_path = path if path else self._path
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(
                json.dumps(self._turns, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            logger.debug("Could not persist conversation: %s", e)

    def append(self, user: str, assistant: str, provider: str = "", model: str = "", 
               tier: str = "", session_id: str = "default") -> None:
        """Record one turn (user query + LLM response).
        
        If session_id is an n8n session, store in isolated file.
        """
        if self._is_isolated_session(session_id):
            # Use isolated session storage
            session_path = self._get_session_path(session_id)
            if session_id not in self._isolated_sessions:
                self._isolated_sessions[session_id] = self._load(session_path)
            
            self._isolated_sessions[session_id].append({
                "timestamp": round(time.time(), 2),
                "user": user,
                "assistant": assistant,
                "provider": provider,
                "model": model,
                "tier": tier,
            })
            
            # Trim to max turns
            if len(self._isolated_sessions[session_id]) > MAX_TURNS:
                self._isolated_sessions[session_id] = self._isolated_sessions[session_id][-MAX_TURNS:]
            
            # Persist isolated session
            try:
                session_path.write_text(
                    json.dumps(self._isolated_sessions[session_id], indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except OSError as e:
                logger.debug("Could not persist isolated session %s: %s", session_id, e)
        else:
            # Default behavior for regular sessions
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

    def messages(self, limit: int = 20, session_id: str = "default") -> List[Dict[str, str]]:
        """Chat-format history to feed any provider on (re)start or fallback.
        
        If session_id is an n8n session, load from isolated storage.
        """
        if self._is_isolated_session(session_id):
            session_path = self._get_session_path(session_id)
            if session_id not in self._isolated_sessions:
                self._isolated_sessions[session_id] = self._load(session_path)
            
            turns = self._isolated_sessions.get(session_id, [])[-limit:]
        else:
            turns = self._turns[-limit:]
        
        messages: List[Dict[str, str]] = []
        for turn in turns:
            if turn.get("user"):
                messages.append({"role": "user", "content": turn["user"]})
            if turn.get("assistant"):
                messages.append({"role": "assistant", "content": turn["assistant"]})
        return messages

    def last_turns(self, limit: int = 5, session_id: str = "default") -> List[Dict[str, Any]]:
        """Get last N turns for a specific session."""
        if self._is_isolated_session(session_id):
            session_path = self._get_session_path(session_id)
            if session_id not in self._isolated_sessions:
                self._isolated_sessions[session_id] = self._load(session_path)
            return self._isolated_sessions.get(session_id, [])[-limit:]
        return self._turns[-limit:]

    def clear(self, session_id: str = "default") -> None:
        """Clear conversation history for a specific session."""
        if self._is_isolated_session(session_id):
            session_path = self._get_session_path(session_id)
            self._isolated_sessions[session_id] = []
            try:
                session_path.unlink(missing_ok=True)
            except OSError:
                pass
        else:
            self._turns = []
            self._save()


conversation_store = ConversationStore()
