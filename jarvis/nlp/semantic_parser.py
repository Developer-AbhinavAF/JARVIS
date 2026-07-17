"""Semantic parser for JARVIS NLP engine.

Performs deep sentence understanding: parses the grammatical structure,
extracts action-object relationships, detects compound sentences, and
produces a structured representation of what the user wants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .utils import tokenize, remove_stop_words, GoalCategory


# ════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class ActionObject:
    """A parsed action-object pair from the sentence."""
    action: str            # The verb/action (e.g., "open", "search", "play")
    object: str            # The target/object (e.g., "youtube", "python tutorial")
    modifiers: list[str] = field(default_factory=list)  # Adverbs, adjectives
    prepositions: list[str] = field(default_factory=list)  # "on", "in", "for"
    raw_span: str = ""     # The original text span


@dataclass
class SentenceStructure:
    """Parsed structure of a sentence."""
    raw_text: str
    actions: list[ActionObject] = field(default_factory=list)
    question_word: str = ""     # "what", "how", "where", etc.
    is_question: bool = False
    is_command: bool = False
    is_compound: bool = False    # Has multiple clauses
    is_negation: bool = False
    subject: str = ""           # Who/what the sentence is about
    tokens: list[str] = field(default_factory=list)
    content_tokens: list[str] = field(default_factory=list)  # Without stop words


# ════════════════════════════════════════════════════════════════════
# ACTION VERBS (semantic grouping, not keyword matching)
# ════════════════════════════════════════════════════════════════════

_ACTION_GROUPS: dict[str, list[str]] = {
    "open": [
        "open", "launch", "start", "run", "fire", "boot", "bring",
        "load", "access", "enter", "go", "visit", "navigate",
    ],
    "close": [
        "close", "shut", "kill", "stop", "quit", "exit", "terminate",
        "end",
    ],
    "search": [
        "search", "find", "look", "google", "query", "browse",
        "seek", "hunt", "check",
    ],
    "play": [
        "play", "watch", "listen", "stream", "put", "spin",
    ],
    "control": [
        "increase", "decrease", "raise", "lower", "turn", "set",
        "mute", "unmute", "minimize", "maximize", "restore",
    ],
    "create": [
        "create", "make", "new", "add", "write", "build",
    ],
    "delete": [
        "delete", "remove", "trash", "clear", "destroy",
    ],
    "copy": [
        "copy", "paste", "cut", "duplicate", "clone",
    ],
    "system": [
        "shutdown", "restart", "reboot", "sleep", "lock", "logout",
    ],
    "capture": [
        "take", "capture", "grab", "snapshot", "screenshot",
    ],
    "get": [
        "get", "fetch", "show", "display", "tell", "give",
        "retrieve", "pull",
    ],
    "save": [
        "save", "store", "remember", "keep", "note",
    ],
    "recall": [
        "recall", "retrieve", "search",
    ],
}

# Reverse map: verb -> action group
_VERB_TO_ACTION: dict[str, str] = {}
for group, verbs in _ACTION_GROUPS.items():
    for verb in verbs:
        _VERB_TO_ACTION[verb] = group

# Question words
_QUESTION_WORDS = {"what", "who", "where", "when", "why", "how", "which", "whose", "whom"}

# Negation words
_NEGATION_WORDS = {"not", "don't", "dont", "no", "never", "neither", "nobody", "nothing"}


# ════════════════════════════════════════════════════════════════════
# SEMANTIC PARSER
# ════════════════════════════════════════════════════════════════════

class SemanticParser:
    """Parses user input into structured semantic representation.

    Unlike a traditional parser, this focuses on action-object pairs
    and semantic roles rather than strict grammar.
    """

    def __init__(self) -> None:
        # Compound separators
        self._compound_seps = re.compile(
            r"\b(?:and|then|also|next|after\s+that|followed\s+by|&|\+)\b",
            re.IGNORECASE,
        )

    def parse(self, text: str) -> SentenceStructure:
        """Parse text into semantic structure.

        Steps:
        1. Tokenize and classify
        2. Detect sentence type (question/command/statement)
        3. Extract action-object pairs
        4. Handle compound sentences
        """
        text = text.strip()
        if not text:
            return SentenceStructure(raw_text=text)

        tokens = tokenize(text)
        content_tokens = remove_stop_words(tokens)

        structure = SentenceStructure(
            raw_text=text,
            tokens=tokens,
            content_tokens=content_tokens,
        )

        # Detect sentence type
        structure.is_question = self._is_question(text, tokens)
        structure.question_word = self._get_question_word(tokens)
        structure.is_negation = self._has_negation(tokens)
        structure.is_command = self._is_command(text, tokens)
        structure.is_compound = self._is_compound(text)

        # Extract action-object pairs
        if structure.is_compound:
            structure.actions = self._parse_compound(text)
        else:
            action = self._extract_action_object(text, tokens, content_tokens)
            if action:
                structure.actions.append(action)

        # Extract subject
        structure.subject = self._extract_subject(tokens, content_tokens)

        return structure

    def _is_question(self, text: str, tokens: list[str]) -> bool:
        """Detect if the input is a question."""
        if text.rstrip().endswith("?"):
            return True
        if tokens and tokens[0] in _QUESTION_WORDS:
            return True
        # Check for question patterns
        first_two = " ".join(tokens[:2]) if len(tokens) >= 2 else ""
        if first_two in ("what is", "what's", "how do", "how does", "who is",
                         "where is", "when is", "why is", "can you"):
            return True
        return False

    def _get_question_word(self, tokens: list[str]) -> str:
        """Get the question word if present."""
        if tokens and tokens[0] in _QUESTION_WORDS:
            return tokens[0]
        return ""

    def _has_negation(self, tokens: list[str]) -> bool:
        """Check for negation."""
        return any(t in _NEGATION_WORDS for t in tokens)

    def _is_command(self, text: str, tokens: list[str]) -> bool:
        """Detect if the input is a command/imperative."""
        if not tokens:
            return False
        first = tokens[0]
        # If first word is an action verb, it's likely a command
        if first in _VERB_TO_ACTION:
            return True
        # Politeness markers followed by verb: "please open", "could you search"
        if first in ("please", "pls", "plz") and len(tokens) > 1:
            return tokens[1] in _VERB_TO_ACTION
        if len(tokens) > 2:
            phrase = f"{tokens[0]} {tokens[1]}"
            if phrase in ("can you", "could you", "would you", "will you"):
                return len(tokens) > 2 and tokens[2] in _VERB_TO_ACTION
        return False

    def _is_compound(self, text: str) -> bool:
        """Detect if text contains multiple commands."""
        return bool(self._compound_seps.search(text))

    def _extract_action_object(
        self, text: str, tokens: list[str], content_tokens: list[str]
    ) -> ActionObject | None:
        """Extract the primary action-object pair from a sentence."""
        if not tokens:
            return None

        # Find the action verb
        action_group = None
        action_verb = ""
        action_idx = -1

        for i, token in enumerate(tokens):
            if token in _VERB_TO_ACTION:
                action_group = _VERB_TO_ACTION[token]
                action_verb = token
                action_idx = i
                break

        # Check for multi-word verbs: "fire up", "shut down", "look up", etc.
        if action_idx == -1 and len(tokens) >= 2:
            for i in range(len(tokens) - 1):
                bigram = f"{tokens[i]} {tokens[i + 1]}"
                if bigram in _VERB_TO_ACTION:
                    action_group = _VERB_TO_ACTION[bigram]
                    action_verb = bigram
                    action_idx = i
                    break

        if action_group is None:
            # No action verb found - treat content as the object
            # e.g., "youtube" → action="open", object="youtube"
            return ActionObject(
                action="open",
                object=" ".join(content_tokens) if content_tokens else text,
                raw_span=text,
            )

        # Everything after the verb is the object (simplified)
        object_tokens = tokens[action_idx + len(action_verb.split()):]
        # Remove trailing politeness markers
        politeness = {"please", "pls", "plz", "for", "me", "now", "thanks"}
        object_tokens = [t for t in object_tokens if t not in politeness]

        obj_text = " ".join(object_tokens).strip()

        return ActionObject(
            action=action_group,
            object=obj_text if obj_text else text,
            raw_span=text,
        )

    def _parse_compound(self, text: str) -> list[ActionObject]:
        """Parse a compound sentence into multiple action-object pairs."""
        # Split on compound separators
        parts = self._compound_seps.split(text)
        actions = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            tokens = tokenize(part)
            content_tokens = remove_stop_words(tokens)
            action = self._extract_action_object(part, tokens, content_tokens)
            if action:
                actions.append(action)
        return actions

    def _extract_subject(self, tokens: list[str], content_tokens: list[str]) -> str:
        """Extract the subject of the sentence (best effort)."""
        # For questions: subject is usually after question word
        if tokens and tokens[0] in _QUESTION_WORDS:
            # "what is the weather" → "weather"
            # "how is my computer" → "computer"
            non_stop = [t for t in tokens[1:] if t not in {"is", "are", "was", "the", "a", "an", "my", "your"}]
            if non_stop:
                return non_stop[0]
        # For commands: subject is the object
        if content_tokens:
            return content_tokens[-1]
        return ""
