"""Context Compression — Retrieve, rank, compress, summarize.

Never send entire documents to the LLM.
Only relevant information should be used.
"""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ContextCompressor:
    """Compress and summarize context for LLM consumption.

    Pipeline: Retrieve -> Rank -> Compress -> Summarize -> Send Context
    """

    def __init__(self, max_tokens: int = 2000) -> None:
        self._max_tokens = max_tokens
        self._compression_count: int = 0

    def compress(
        self,
        contexts: list[str],
        query: str = "",
        max_tokens: int | None = None,
    ) -> str:
        """Compress multiple context pieces into a single concise context."""
        limit = max_tokens or self._max_tokens
        self._compression_count += 1

        if not contexts:
            return ""

        # Deduplicate
        unique = list(dict.fromkeys(contexts))

        # Score relevance to query
        if query:
            scored = [(c, self._relevance_score(c, query)) for c in unique]
            scored.sort(key=lambda x: -x[1])
            unique = [c for c, _ in scored]

        # Truncate to token limit (approximate: 1 token ~ 4 chars)
        max_chars = limit * 4
        result_parts: list[str] = []
        total_chars = 0

        for context in unique:
            if total_chars + len(context) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    result_parts.append(context[:remaining] + "...")
                break
            result_parts.append(context)
            total_chars += len(context)

        return "\n\n".join(result_parts)

    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """Extractive summary — pick most important sentences."""
        if not text:
            return ""

        sentences = self._split_sentences(text)
        if len(sentences) <= max_sentences:
            return text

        # Score sentences by importance
        scored = [(s, self._sentence_score(s)) for s in sentences]
        scored.sort(key=lambda x: -x[1])

        # Return top sentences in original order
        top_indices = set()
        for s, _ in scored[:max_sentences]:
            idx = sentences.index(s)
            top_indices.add(idx)

        result = [sentences[i] for i in sorted(top_indices)]
        return " ".join(result)

    def extract_key_info(self, text: str, query: str = "") -> list[str]:
        """Extract key pieces of information from text."""
        lines = text.split("\n")
        key_info: list[str] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Headers are key info
            if line.startswith("#") or line.startswith("**"):
                key_info.append(line)
            # Lists are key info
            elif line.startswith(("- ", "* ", "1.", "2.", "3.")):
                key_info.append(line)
            # Lines with high-value keywords
            elif any(kw in line.lower() for kw in (
                "important", "note", "warning", "key", "summary",
                "conclusion", "result", "answer", "solution",
            )):
                key_info.append(line)

        return key_info

    def _relevance_score(self, text: str, query: str) -> float:
        """Simple keyword overlap relevance scoring."""
        if not query:
            return 0.5
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        if not query_words:
            return 0.0
        overlap = len(query_words & text_words)
        return overlap / len(query_words)

    def _sentence_score(self, sentence: str) -> float:
        """Score sentence importance."""
        score = 0.5
        # First and last sentences are often important
        # Headers/definitions
        if ":" in sentence:
            score += 0.1
        # Contains numbers/data
        if any(c.isdigit() for c in sentence):
            score += 0.1
        # Contains important keywords
        important_words = [
            "important", "key", "summary", "conclusion", "result",
            "answer", "solution", "definition", "example", "note",
        ]
        if any(w in sentence.lower() for w in important_words):
            score += 0.2
        # Length penalty for very short or very long
        words = len(sentence.split())
        if 5 < words < 30:
            score += 0.1
        return min(1.0, score)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        return re.split(r'(?<=[.!?])\s+', text)

    def get_stats(self) -> dict[str, Any]:
        return {
            "max_tokens": self._max_tokens,
            "compression_count": self._compression_count,
        }


context_compressor = ContextCompressor()

__all__ = ["ContextCompressor", "context_compressor"]
