"""CallManager — manages active call sessions.

Tracks all active calls, provides lookup by SID, and handles cleanup.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Optional

from interface.telephony.session import CallSession, AudioState
from interface.telephony.logger import CallLogger, LatencyRecord

logger = logging.getLogger("jarvis.telephony")


class CallManager:
    """Singleton managing all active phone call sessions."""

    def __init__(self) -> None:
        self._active: dict[str, CallSession] = {}
        self._loggers: dict[str, CallLogger] = {}
        self._history: list[dict[str, Any]] = []

    def create_session(self, call_sid: str, caller_number: str) -> CallSession:
        session = CallSession(call_sid=call_sid, caller_number=caller_number)
        self._active[call_sid] = session
        self._loggers[call_sid] = CallLogger(call_sid=call_sid, caller=caller_number)
        logger.info("📞 Call session created: %s from %s", call_sid, caller_number)
        return session

    def get_session(self, call_sid: str) -> Optional[CallSession]:
        return self._active.get(call_sid)

    def get_logger(self, call_sid: str) -> Optional[CallLogger]:
        return self._loggers.get(call_sid)

    def end_session(self, call_sid: str) -> Optional[CallSession]:
        session = self._active.pop(call_sid, None)
        log = self._loggers.pop(call_sid, None)
        if session:
            session.set_audio_state(AudioState.IDLE)
            self._history.append(session.to_dict())
            if log:
                log.finalize()
            logger.info("📞 Call session ended: %s (%.0fs, %d turns)",
                        call_sid, session.duration_sec, len(session.turns))
        return session

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def active_sessions(self) -> list[CallSession]:
        return list(self._active.values())

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    async def broadcast_state(self, call_sid: str) -> None:
        """Push audio state to connected WebSocket clients (for Web UI)."""
        session = self.get_session(call_sid)
        if not session:
            return
        # Broadcast to any WebSocket subscribers (Web UI phone panel)
        from interface.telephony.twilio_server import _ws_subscribers
        msg = {
            "type": "call_state",
            "data": session.to_dict(),
        }
        disconnected = set()
        for ws in _ws_subscribers:
            try:
                await ws.send_json(msg)
            except Exception:
                disconnected.add(ws)
        _ws_subscribers.difference_update(disconnected)


call_manager = CallManager()
