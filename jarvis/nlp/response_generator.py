"""Response generator for JARVIS NLP.

Generates context-dependent responses. The response style depends on:
- Question -> Answer
- Command -> Confirmation
- Search -> Result
- Analysis -> Insights
- Coding -> Code
- Conversation -> Natural Reply

Never uses the same template twice.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from jarvis.nlp.utils import ExecutionMode, GoalCategory


@dataclass
class ResponseTemplate:
    intent: str
    templates: list[str]
    style: str = "standard"

    def pick(self) -> str:
        return random.choice(self.templates) if self.templates else ""


_TEMPLATES: dict[str, ResponseTemplate] = {
    "GREETING": ResponseTemplate(
        "GREETING",
        ["Hey! How can I help?", "Hello! What can I do for you?", "Hi there! Ready when you are."],
        style="friendly",
    ),
    "CHAT": ResponseTemplate(
        "CHAT",
        ["I'm doing great, thanks for asking!", "I'm here and ready to help!", "All good on my end! What can I do for you?"],
        style="friendly",
    ),
    "GET_WEATHER": ResponseTemplate(
        "GET_WEATHER",
        ["Here's the weather:", "Weather update:", "Current conditions:"],
        style="informative",
    ),
    "DATETIME": ResponseTemplate(
        "DATETIME",
        ["It's {time}.", "Current time: {time}", "The time is {time}."],
        style="concise",
    ),
    "JOKE": ResponseTemplate(
        "JOKE",
        ["Here's one:", "Sure, here goes:", "Okay, listen:"],
        style="entertaining",
    ),
    "OPEN_WEBSITE": ResponseTemplate(
        "OPEN_WEBSITE",
        ["Opening {target}.", "Navigating to {target}.", "Let me open {target}."],
        style="confirmation",
    ),
    "OPEN_APP": ResponseTemplate(
        "OPEN_APP",
        ["Opening {target}.", "Launching {target}.", "Starting {target}."],
        style="confirmation",
    ),
    "SEARCH_WEB": ResponseTemplate(
        "SEARCH_WEB",
        ["Searching for {query}.", "Let me look that up.", "Here's what I found:"],
        style="informative",
    ),
    "VOLUME_CONTROL": ResponseTemplate(
        "VOLUME_CONTROL",
        ["Volume adjusted.", "Done.", "Volume updated."],
        style="concise",
    ),
    "BRIGHTNESS_CONTROL": ResponseTemplate(
        "BRIGHTNESS_CONTROL",
        ["Brightness adjusted.", "Screen brightness updated.", "Done."],
        style="concise",
    ),
    "SCREENSHOT": ResponseTemplate(
        "SCREENSHOT",
        ["Screenshot saved.", "Captured!", "Screenshot taken."],
        style="concise",
    ),
    "SAVE_MEMORY": ResponseTemplate(
        "SAVE_MEMORY",
        ["Got it, I'll remember that.", "Saved.", "I'll keep that in mind."],
        style="confirmation",
    ),
    "RECALL_MEMORY": ResponseTemplate(
        "RECALL_MEMORY",
        ["Here's what I remember:", "Let me check my memory:", "I found this:"],
        style="informative",
    ),
    "PROGRAMMING": ResponseTemplate(
        "PROGRAMMING",
        ["Opening your coding environment.", "Let me set up your IDE.", "Starting coding session."],
        style="confirmation",
    ),
    "CALCULATOR": ResponseTemplate(
        "CALCULATOR",
        ["The result is {result}.", "That equals {result}.", "{result}"],
        style="concise",
    ),
    "FLIP_COIN": ResponseTemplate(
        "FLIP_COIN",
        ["It's {result}.", "The coin landed on {result}.", "{result}!"],
        style="entertaining",
    ),
    "SYSTEM_STATUS": ResponseTemplate(
        "SYSTEM_STATUS",
        ["Here's your system status:", "System overview:", "Current system state:"],
        style="informative",
    ),
}

# Emotion-modified response prefixes
_EMOTION_PREFIXES: dict[str, list[str]] = {
    "frustrated": ["I understand this is frustrating. ", "Let me help fix this. "],
    "confused": ["No worries, let me explain. ", ""],
    "excited": ["", ""],
    "tired": ["", "Just a quick one: "],
    "angry": ["I hear you. ", ""],
    "sad": ["I'm here to help. ", ""],
}


@dataclass
class GeneratedResponse:
    text: str
    style: str
    is_confirmation: bool
    is_error: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "style": self.style,
            "is_confirmation": self.is_confirmation,
            "is_error": self.is_error,
        }


class ResponseGenerator:
    """Generates context-dependent responses based on intent, emotion, and context.

    Adapts tone and content based on the user's emotional state and
    the type of action being performed.
    """

    def generate(
        self,
        intent: str,
        entities: dict[str, Any],
        tool_result: Any = None,
        execution_mode: ExecutionMode = ExecutionMode.AUTO,
        emotion: str = "neutral",
        context: dict[str, Any] | None = None,
        error: str = "",
    ) -> GeneratedResponse:
        """Generate a response for the given NLP output."""
        if error:
            return self._error_response(error, intent, emotion)

        template = _TEMPLATES.get(intent)
        if not template:
            return self._fallback_response(intent, entities, emotion)

        text = template.pick()
        style = template.style

        # Fill placeholders
        target = str(entities.get("target", ""))
        query = str(entities.get("query", ""))
        city = str(entities.get("city", ""))
        result = str(entities.get("result", ""))

        text = text.replace("{target}", target or query or city)
        text = text.replace("{query}", query)
        text = text.replace("{result}", result)
        text = text.replace("{time}", result)

        # Add emotion prefix
        if emotion in _EMOTION_PREFIXES:
            prefix = random.choice(_EMOTION_PREFIXES[emotion])
            text = prefix + text

        is_confirmation = style == "confirmation"

        return GeneratedResponse(
            text=text,
            style=style,
            is_confirmation=is_confirmation,
            is_error=False,
        )

    def generate_clarification(
        self,
        intent: str,
        missing_info: list[str],
    ) -> GeneratedResponse:
        """Generate a clarification question."""
        if len(missing_info) == 1:
            text = f"Could you tell me the {missing_info[0]}?"
        elif len(missing_info) == 2:
            text = f"Could you provide the {missing_info[0]} and {missing_info[1]}?"
        else:
            text = "Could you provide more details?"

        return GeneratedResponse(
            text=text,
            style="clarification",
            is_confirmation=False,
            is_error=False,
        )

    def generate_suggestion(
        self,
        suggestions: list[str],
        emotion: str = "neutral",
    ) -> GeneratedResponse:
        """Generate a suggestion response."""
        if not suggestions:
            return GeneratedResponse(
                text="How can I help?",
                style="suggestion",
                is_confirmation=False,
                is_error=False,
            )

        options = "\n".join(f"  - {s}" for s in suggestions[:5])
        text = f"I can help with:\n{options}"

        return GeneratedResponse(
            text=text,
            style="suggestion",
            is_confirmation=False,
            is_error=False,
        )

    @staticmethod
    def _error_response(
        error: str,
        intent: str,
        emotion: str,
    ) -> GeneratedResponse:
        """Generate an error response."""
        if "not found" in error.lower():
            text = "I couldn't find what you're looking for. Would you like me to search for it?"
        elif "timeout" in error.lower():
            text = "That took too long. Would you like me to try again?"
        elif "permission" in error.lower():
            text = "I don't have permission to do that."
        else:
            text = f"Something went wrong: {error}. Want me to try an alternative?"

        return GeneratedResponse(
            text=text,
            style="error",
            is_confirmation=False,
            is_error=True,
        )

    @staticmethod
    def _fallback_response(
        intent: str,
        entities: dict[str, Any],
        emotion: str,
    ) -> GeneratedResponse:
        """Generate a fallback response for unknown intents."""
        target = str(entities.get("target", entities.get("query", "")))
        if target:
            text = f"Done: {target}"
        else:
            text = "Done."

        return GeneratedResponse(
            text=text,
            style="confirmation",
            is_confirmation=True,
            is_error=False,
        )
