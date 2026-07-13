"""Command parsing for JARVIS NLP pipeline.

Handles multi-command parsing, command chains, and compound commands.
Supports natural language compound commands like:
- "Open Chrome and search FastAPI on GitHub"
- "Play Believer and lower volume to 30%"
- "Open VS Code and launch my Python project"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ParsedCommand:
    """A single parsed command."""
    text: str
    intent: str | None = None
    action: str | None = None
    params: dict = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class CommandChain:
    """A chain of commands to execute in sequence."""
    commands: list[ParsedCommand] = field(default_factory=list)
    raw_text: str = ""
    is_multi: bool = False

    @property
    def count(self) -> int:
        return len(self.commands)

    @property
    def first(self) -> ParsedCommand | None:
        return self.commands[0] if self.commands else None


class CommandParser:
    """Parses user input into one or more commands.

    Handles:
    - Single commands: "open youtube"
    - Compound commands: "open youtube and search for music"
    - Sequential commands: "open chrome then search for python"
    - Parallel commands: "open youtube and open spotify"
    - Complex multi-intent: "Play Believer and lower volume to 30%"
    """

    # Split markers that indicate multiple commands
    SPLIT_MARKERS = [
        " and ", " then ", " also ", " next ", " after that ",
        " followed by ", " & ", " + ", " ; ",
        "while ", "whilst ",
    ]

    # Command starters that indicate a new command
    COMMAND_STARTERS = [
        "open ", "close ", "launch ", "start ", "quit ", "kill ",
        "play ", "stop ", "pause ", "resume ", "skip ", "next ",
        "move ", "click ", "double click ", "right click ",
        "type ", "press ", "hold ",
        "set volume", "volume ", "mute", "unmute",
        "set brightness", "brightness ",
        "take ", "capture ", "save ", "delete ",
        "search ", "find ", "look up ", "google ", "youtube ",
        "what ", "when ", "where ", "who ", "why ", "how ",
        "tell me ", "show ", "get ", "check ", "list ", "status",
        "add ", "create ", "new ", "remember ", "note ",
        "remove ", "clear ", "complete ", "finish ", "mark ",
        "send ", "email ", "message ", "call ",
        "schedule ", "remind ", "alarm ",
        "shutdown ", "restart ", "reboot ", "sleep ", "lock ",
        "lower ", "raise ", "increase ", "decrease ",
        "turn ", "make ", "set ",
    ]

    # Patterns that indicate a new command after a split marker
    _NEW_COMMAND_PATTERNS = re.compile(
        r"^(?:open|launch|start|run|close|kill|stop|quit|exit|"
        r"play|pause|resume|stop|skip|next|"
        r"search|find|look|google|"
        r"what|when|where|who|why|how|"
        r"tell|show|get|check|list|"
        r"add|create|remove|delete|clear|"
        r"set|turn|make|raise|lower|increase|decrease|"
        r"take|capture|save|send|email|call|"
        r"shutdown|restart|reboot|sleep|lock|"
        r"remember|note|remind|schedule)",
        re.IGNORECASE,
    )

    def parse(self, text: str) -> CommandChain:
        """Parse text into a command chain.

        Args:
            text: Raw user input

        Returns:
            CommandChain with parsed commands
        """
        cleaned = text.strip()
        if not cleaned:
            return CommandChain(raw_text=text)

        # Try to split into multiple commands
        parts = self._split_commands(cleaned)

        if len(parts) <= 1:
            # Single command
            cmd = ParsedCommand(text=cleaned)
            return CommandChain(
                commands=[cmd],
                raw_text=text,
                is_multi=False,
            )

        # Multiple commands
        commands = [ParsedCommand(text=part.strip()) for part in parts if part.strip()]
        return CommandChain(
            commands=commands,
            raw_text=text,
            is_multi=True,
        )

    def _split_commands(self, text: str) -> list[str]:
        """Split text into multiple commands."""
        text_lower = text.lower()

        # Try each split marker
        for marker in self.SPLIT_MARKERS:
            if marker not in text_lower:
                continue

            # Find all occurrences of this marker
            parts = text.split(marker, 1)
            if len(parts) != 2:
                continue

            before = parts[0].strip()
            after = parts[1].strip()

            if not before or not after:
                continue

            # Check if the part after the marker starts with a new command
            is_new_command = bool(self._NEW_COMMAND_PATTERNS.match(after))

            if is_new_command:
                # This is a genuine multi-command split
                # But we need to handle cases where "and" is part of a single command
                # e.g., "what is 2 and 2" should NOT be split
                # Check if the before part looks like a complete command
                if self._looks_like_complete_command(before):
                    return [before, after]
                else:
                    # "and" might be part of the command (e.g., "what is 2 and 2")
                    # Don't split
                    continue

            # Even if after doesn't start with a command starter,
            # check if it looks like a command based on verb presence
            if self._has_command_verb(after):
                if self._looks_like_complete_command(before):
                    return [before, after]

        return [text]

    def _looks_like_complete_command(self, text: str) -> bool:
        """Check if text looks like a complete command."""
        text_lower = text.lower().strip()

        # Very short text is likely not a complete command
        if len(text_lower) < 3:
            return False

        # If it starts with a command verb, it's likely complete
        if self._NEW_COMMAND_PATTERNS.match(text_lower):
            return True

        # If it's a known entity name (app, website), it's complete
        known_entities = {
            "youtube", "google", "github", "reddit", "spotify", "netflix",
            "chrome", "firefox", "edge", "notepad", "calculator", "vscode",
            "discord", "steam", "whatsapp", "telegram", "slack", "zoom",
        }
        if text_lower in known_entities:
            return True

        # If it contains a question word, it's likely complete
        question_words = {"what", "when", "where", "who", "why", "how", "which"}
        if any(text_lower.startswith(q) for q in question_words):
            return True

        return False

    def _has_command_verb(self, text: str) -> bool:
        """Check if text contains a command verb."""
        return bool(self._NEW_COMMAND_PATTERNS.match(text.strip()))

    def is_multi_command(self, text: str) -> bool:
        """Quick check if text contains multiple commands."""
        text_lower = text.lower()
        for marker in self.SPLIT_MARKERS:
            if marker in text_lower:
                return True
        return False


# Global instance
command_parser = CommandParser()
