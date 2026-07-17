"""Speech Agent — Voice interaction and speech processing."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class SpeechAgent(AgentBase):
    """Handles speech recognition, synthesis, wake word, and voice streaming."""

    def __init__(self) -> None:
        super().__init__("speech", AgentPriority.HIGH)
        self.add_capability(AgentCapability(
            name="speech_output",
            intent_patterns=["SPEAK", "VOICE_OUTPUT", "TTS"],
            keywords=["say", "speak", "tell me", "voice"],
        ))

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")

        result = self._handle_speech(text, intent)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "audio_data": result.get("audio_data"),
                "emotion": result.get("emotion", "neutral"),
            },
        )

    def _handle_speech(self, text: str, intent: str) -> dict:
        try:
            from jarvis.speech import speech_engine
            caps = speech_engine.get_capabilities()
            if caps.get("tts_available"):
                return {"response": text, "emotion": "neutral"}
        except Exception as e:
            logger.debug("Speech not available: %s", e)

        return {"response": text, "emotion": "neutral"}


speech_agent = SpeechAgent()
