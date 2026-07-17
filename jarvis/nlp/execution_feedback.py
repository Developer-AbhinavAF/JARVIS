"""Execution feedback pipeline for JARVIS NLP.

Provides UI status messages for every phase of the NLP pipeline:
Listening... -> Understanding... -> Detecting Intent... -> Planning...
-> Searching... -> Analyzing... -> Opening... -> Reading... -> Writing...
-> Coding... -> Executing... -> Learning... -> Updating Memory... -> Done

Never stays silent.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


PHASE_MESSAGES: dict[str, list[str]] = {
    "listening": ["Listening..."],
    "understanding": ["Understanding...", "Processing input..."],
    "normalizing": ["Normalizing text...", "Cleaning input..."],
    "language_detection": ["Detecting language..."],
    "context_resolution": ["Resolving context...", "Checking conversation history..."],
    "intent_detection": ["Detecting intent...", "Understanding what you mean..."],
    "entity_extraction": ["Extracting entities...", "Identifying key information..."],
    "emotion_detection": ["Reading emotional tone..."],
    "implicit_intent": ["Looking for implied goals..."],
    "conversation_analysis": ["Analyzing conversation type..."],
    "goal_detection": ["Determining your goal...", "Figuring out what you need..."],
    "capability_detection": ["Checking capabilities...", "Verifying system resources..."],
    "tool_resolution": ["Selecting the right tool...", "Finding the best approach..."],
    "parameter_building": ["Preparing parameters...", "Setting up action..."],
    "planning": ["Planning execution...", "Creating action plan..."],
    "safety_check": ["Running safety checks...", "Validating action..."],
    "confidence_scoring": ["Evaluating confidence...", "Assessing certainty..."],
    "searching": ["Searching...", "Looking that up..."],
    "analyzing": ["Analyzing...", "Processing results..."],
    "opening": ["Opening...", "Launching..."],
    "reading": ["Reading...", "Loading content..."],
    "writing": ["Writing...", "Saving..."],
    "coding": ["Coding...", "Working on it..."],
    "executing": ["Executing...", "Running..."],
    "learning": ["Learning from interaction..."],
    "memory_update": ["Updating memory...", "Storing for next time..."],
    "done": ["Done!", "All set!", "Complete!"],
    "error": ["Something went wrong...", "Encountered an issue..."],
    "fallback": ["Let me try a different approach...", "Falling back to LLM..."],
}


@dataclass
class FeedbackMessage:
    """A single feedback message for the UI."""
    phase: str
    message: str
    timestamp: float = 0.0
    progress: float = 0.0  # 0.0 to 1.0
    is_final: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "message": self.message,
            "timestamp": self.timestamp,
            "progress": self.progress,
            "is_final": self.is_final,
        }


@dataclass
class FeedbackSession:
    """Tracks feedback for a single NLP processing session."""
    session_id: str = ""
    messages: list[FeedbackMessage] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration_ms(self) -> float:
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time > 0 else time.time()
        return (end - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
            "duration_ms": round(self.duration_ms, 1),
        }


class ExecutionFeedback:
    """Provides real-time status feedback for the NLP pipeline.

    Generates phase-appropriate messages that can be displayed in the
    UI to keep the user informed during processing.
    """

    def __init__(self) -> None:
        self._current_session: FeedbackSession | None = None
        self._callback: Any = None

    def set_callback(self, callback: Any) -> None:
        """Set a callback function for real-time feedback updates.

        The callback receives FeedbackMessage objects as they are generated.
        """
        self._callback = callback

    def start_session(self, session_id: str = "") -> FeedbackSession:
        """Start a new feedback session."""
        self._current_session = FeedbackSession(
            session_id=session_id,
            start_time=time.time(),
        )
        return self._current_session

    def update(self, phase: str, custom_message: str = "") -> FeedbackMessage:
        """Send a feedback update for the given phase.

        Parameters
        ----------
        phase:
            The current pipeline phase (e.g. "intent_detection").
        custom_message:
            Optional custom message override.

        Returns
        -------
        The FeedbackMessage that was generated.
        """
        if not self._current_session:
            self.start_session()

        messages = PHASE_MESSAGES.get(phase, [f"{phase}..."])
        message_text = custom_message or messages[0]

        progress = self._estimate_progress(phase)
        is_final = phase in ("done", "error", "fallback")

        msg = FeedbackMessage(
            phase=phase,
            message=message_text,
            timestamp=time.time(),
            progress=progress,
            is_final=is_final,
        )

        self._current_session.messages.append(msg)

        if is_final:
            self._current_session.end_time = time.time()

        if self._callback:
            try:
                self._callback(msg)
            except Exception:
                pass

        return msg

    def finish(self, success: bool = True) -> FeedbackSession | None:
        """Finish the current feedback session."""
        if not self._current_session:
            return None

        phase = "done" if success else "error"
        self.update(phase)

        session = self._current_session
        self._current_session = None
        return session

    def get_all_phases(self) -> list[str]:
        """Return all available phase names."""
        return list(PHASE_MESSAGES.keys())

    @staticmethod
    def _estimate_progress(phase: str) -> float:
        """Estimate progress (0.0 to 1.0) based on phase name."""
        phase_order = [
            "listening", "understanding", "normalizing",
            "language_detection", "context_resolution",
            "intent_detection", "entity_extraction",
            "emotion_detection", "implicit_intent",
            "conversation_analysis", "goal_detection",
            "capability_detection", "tool_resolution",
            "parameter_building", "planning",
            "safety_check", "confidence_scoring",
            "executing", "learning", "memory_update",
            "done",
        ]

        try:
            idx = phase_order.index(phase)
            return round(idx / (len(phase_order) - 1), 2)
        except ValueError:
            return 0.5
