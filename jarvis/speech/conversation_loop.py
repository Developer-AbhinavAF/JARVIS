"""Conversation Loop — Continuous conversation state machine.

Manages the listen → think → speak → listen cycle.
Conversation remains continuous until speech mode is disabled.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """States of the conversation loop."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    STOPPED = "stopped"


@dataclass
class ConversationTurn:
    """One turn in the conversation."""
    turn_id: int = 0
    user_input: str = ""
    response: str = ""
    emotion: str = "neutral"
    start_time: float = 0.0
    end_time: float = 0.0
    was_interrupted: bool = False

    @property
    def duration_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


class ConversationLoop:
    """State machine for continuous voice conversation.

    Flow: IDLE → LISTENING → THINKING → SPEAKING → LISTENING → ...
    Interrupts: SPEAKING → INTERRUPTED → LISTENING
    """

    def __init__(self) -> None:
        self._state = ConversationState.IDLE
        self._turns: list[ConversationTurn] = []
        self._current_turn: ConversationTurn | None = None
        self._turn_count: int = 0
        self._is_running = False
        self._loop_thread: threading.Thread | None = None

        # Callbacks for each state transition
        self._on_listen: Callable[[], str] | None = None
        self._on_think: Callable[[str], tuple[str, str]] | None = None
        self._on_speak: Callable[[str, str], None] | None = None
        self._on_interrupt: Callable[[], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None

    @property
    def state(self) -> ConversationState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def turns(self) -> list[ConversationTurn]:
        return self._turns

    def configure(
        self,
        on_listen: Callable[[], str] | None = None,
        on_think: Callable[[str], tuple[str, str]] | None = None,
        on_speak: Callable[[str, str], None] | None = None,
        on_interrupt: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Configure state transition callbacks.

        Args:
            on_listen: Called when listening. Returns user input text.
            on_think: Called with user input. Returns (response, emotion).
            on_speak: Called with response text and emotion.
            on_interrupt: Called when interrupted.
            on_error: Called on errors.
        """
        self._on_listen = on_listen
        self._on_think = on_think
        self._on_speak = on_speak
        self._on_interrupt = on_interrupt
        self._on_error = on_error

    def start(self) -> None:
        """Start the conversation loop."""
        if self._is_running:
            return

        self._is_running = True
        self._state = ConversationState.IDLE

        self._loop_thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="conversation-loop",
        )
        self._loop_thread.start()
        logger.info("Conversation loop started")

    def stop(self) -> None:
        """Stop the conversation loop."""
        self._is_running = False
        self._state = ConversationState.STOPPED
        logger.info("Conversation loop stopped")

    def interrupt(self) -> None:
        """Signal an interrupt."""
        if self._state == ConversationState.SPEAKING:
            self._state = ConversationState.INTERRUPTED
            if self._on_interrupt:
                try:
                    self._on_interrupt()
                except Exception as e:
                    logger.debug("Interrupt callback error: %s", e)
            if self._current_turn:
                self._current_turn.was_interrupted = True

    def process_single(self, user_input: str) -> ConversationTurn:
        """Process a single turn without the loop."""
        turn = ConversationTurn(
            turn_id=self._turn_count,
            user_input=user_input,
            start_time=time.time(),
        )
        self._turn_count += 1

        try:
            # Think
            self._state = ConversationState.THINKING
            if self._on_think:
                response, emotion = self._on_think(user_input)
                turn.response = response
                turn.emotion = emotion

            # Speak
            self._state = ConversationState.SPEAKING
            if self._on_speak and turn.response:
                self._on_speak(turn.response, turn.emotion)

        except Exception as e:
            logger.error("Process failed: %s", e)
            if self._on_error:
                self._on_error(e)

        turn.end_time = time.time()
        self._turns.append(turn)
        self._state = ConversationState.IDLE
        return turn

    def _run_loop(self) -> None:
        """Main conversation loop."""
        while self._is_running:
            try:
                # Listen
                self._state = ConversationState.LISTENING
                user_input = ""
                if self._on_listen:
                    user_input = self._on_listen()

                if not user_input or not user_input.strip():
                    continue

                # Create turn
                turn = ConversationTurn(
                    turn_id=self._turn_count,
                    user_input=user_input,
                    start_time=time.time(),
                )
                self._turn_count += 1
                self._current_turn = turn

                # Think
                self._state = ConversationState.THINKING
                if self._on_think:
                    response, emotion = self._on_think(user_input)
                    turn.response = response
                    turn.emotion = emotion

                # Speak
                self._state = ConversationState.SPEAKING
                if self._on_speak and turn.response:
                    self._on_speak(turn.response, turn.emotion)

                turn.end_time = time.time()
                self._turns.append(turn)
                self._current_turn = None

                # Loop continues automatically to LISTENING

            except Exception as e:
                logger.error("Conversation loop error: %s", e)
                if self._on_error:
                    self._on_error(e)
                time.sleep(0.1)

    def get_stats(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "is_running": self._is_running,
            "turn_count": self._turn_count,
            "total_turns": len(self._turns),
            "avg_turn_ms": (
                sum(t.duration_ms for t in self._turns) / len(self._turns)
                if self._turns else 0
            ),
        }


conversation_loop = ConversationLoop()
