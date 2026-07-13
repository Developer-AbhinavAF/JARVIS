"""A modular NLP pipeline built on top of the AI Router.

Each high-level NLP capability is provided as a method that delegates
to the central `router_client`. The prompts here are lightweight
wrappers — in production these should be replaced by robust, tested
prompt templates and optionally a prompt optimization/compression layer.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from jarvis import config
from jarvis.router_service import router_client

logger = logging.getLogger(__name__)


class NLPPipeline:
    """Facade for common NLP tasks using the AI Router.

    Methods return raw text or parsed JSON where appropriate. They are
    intentionally small so teams can replace any stage independently.
    """

    def __init__(self) -> None:
        self.client = router_client

    def _call_llm(self, prompt: str, *, max_tokens: int | None = None, response_format: Dict[str, Any] | None = None) -> str:
        if max_tokens is None:
            max_tokens = config.LLM_MAX_TOKENS
        try:
            return self.client.chat([{"role": "user", "content": prompt}], max_tokens=max_tokens, response_format=response_format)
        except Exception as exc:
            logger.exception("LLM call failed: %s", exc)
            raise

    def detect_intent(self, text: str) -> str:
        prompt = f"Detect the user's intent from the following text. Respond with a single intent label:\n\nText: {text}\n\nIntent:"
        return self._call_llm(prompt, max_tokens=32)

    def classify_intent(self, text: str, intents: List[str]) -> str:
        intents_str = ", ".join(intents)
        prompt = (
            f"Classify the intent of the text into one of: {intents_str}.\n\nText: {text}\n\nIntent:"
        )
        return self._call_llm(prompt, max_tokens=32)

    def recognize_entities(self, text: str) -> Dict[str, Any]:
        prompt = (
            "Extract named entities from the text and return a JSON array of {type, text, start, end}.\n\n"
            f"Text: {text}\n\nReturn JSON:"
        )
        raw = self._call_llm(prompt, max_tokens=256)
        try:
            return json.loads(raw)
        except Exception:
            logger.debug("Entity extractor returned non-JSON, returning raw text")
            return {"raw": raw}

    def pos_tag(self, text: str) -> str:
        prompt = f"Return the POS tags for the sentence in the format token/POS separated by spaces:\n\n{text}\n\nTags:"
        return self._call_llm(prompt, max_tokens=256)

    def dependency_parse(self, text: str) -> str:
        prompt = f"Return a simple dependency parse (head -> dependent: relation) for the sentence:\n\n{text}\n\nParse:"
        return self._call_llm(prompt, max_tokens=256)

    def summarize(self, text: str, max_tokens: int = 120) -> str:
        prompt = f"Summarize the following text concisely:\n\n{text}\n\nSummary:"
        return self._call_llm(prompt, max_tokens=max_tokens)

    def sentiment(self, text: str) -> str:
        prompt = f"Analyze the sentiment of the text. Return one word: positive, neutral, or negative.\n\n{text}\n\nSentiment:"
        return self._call_llm(prompt, max_tokens=16)
