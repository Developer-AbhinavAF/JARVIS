"""Vision Agent — Screen analysis, OCR, and visual reasoning."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class VisionAgent(AgentBase):
    """Handles screen analysis, OCR, UI detection, and visual reasoning."""

    def __init__(self) -> None:
        super().__init__("vision", AgentPriority.HIGH)
        self.add_capability(AgentCapability(
            name="visual_analysis",
            intent_patterns=["VISUAL_ANALYSIS", "SCREEN_LOOK", "OCR", "UI_DETECTION"],
            keywords=["what's on", "screen", "see", "look at", "read this", "ocr",
                     "what error", "what is showing", "what do you see", "describe this"],
        ))

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")

        result = self._analyze(text, intent)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "visual_context": result.get("context", {}),
                "confidence": result.get("confidence", 0.0),
            },
        )

    def _analyze(self, text: str, intent: str) -> dict:
        try:
            from jarvis.vision import VisionEngine
            engine = VisionEngine()
            scene = engine.see()

            if scene:
                return {
                    "response": f"Screen captured: {len(scene.get('text', ''))} characters detected",
                    "context": scene,
                    "confidence": 0.8,
                }
        except Exception as e:
            logger.debug("Vision not available: %s", e)

        return {
            "response": "Visual analysis not available right now.",
            "context": {},
            "confidence": 0.0,
        }


vision_agent = VisionAgent()
