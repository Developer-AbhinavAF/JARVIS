"""Semantic Similarity Engine for JARVIS NLP.

Replaces keyword/token matching with embedding-based semantic similarity.
Every sentence becomes a vector. Every intent has embeddings.
Similarity determines the best intent. Compare meanings, not words.

Uses a lightweight TF-IDF-like approach with cosine similarity
that works without external ML libraries.
"""

from __future__ import annotations

import re
import math
import time
from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# STOP WORDS & VOCABULARY
# ════════════════════════════════════════════════════════════════════

STOP_WORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out",
    "off", "over", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "that",
    "this", "it", "its", "i", "me", "my", "we", "our", "you", "your",
    "he", "him", "his", "she", "her", "they", "them", "their", "what",
    "which", "who", "whom",
}


# ════════════════════════════════════════════════════════════════════
# EMBEDDING MODEL (Lightweight TF-IDF-like)
# ════════════════════════════════════════════════════════════════════

@dataclass
class Embedding:
    """A sparse embedding vector with metadata."""
    vector: dict[str, float] = field(default_factory=dict)
    text: str = ""
    dimension: int = 0

    def cosine_similarity(self, other: Embedding) -> float:
        """Compute cosine similarity between two sparse vectors."""
        if not self.vector or not other.vector:
            return 0.0

        # Find common terms
        common = set(self.vector.keys()) & set(other.vector.keys())
        if not common:
            return 0.0

        dot_product = sum(self.vector[k] * other.vector[k] for k in common)
        norm_a = math.sqrt(sum(v * v for v in self.vector.values()))
        norm_b = math.sqrt(sum(v * v for v in other.vector.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)


class SemanticEmbeddingEngine:
    """Lightweight embedding engine using TF-IDF-like vectorization.

    No external ML libraries required. Works by:
    1. Tokenizing and normalizing text
    2. Computing term frequency (TF)
    3. Applying inverse document frequency (IDF) weights
    4. Computing cosine similarity between embeddings
    """

    def __init__(self) -> None:
        self._document_count: int = 0
        self._document_frequency: dict[str, int] = {}
        self._intent_embeddings: dict[str, Embedding] = {}
        self._build_time: float = 0.0

    def embed(self, text: str) -> Embedding:
        """Convert text to a sparse embedding vector."""
        tokens = self._tokenize(text)
        if not tokens:
            return Embedding(text=text)

        # Compute term frequency
        tf: dict[str, float] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0.0) + 1.0

        # Normalize by document length
        doc_len = len(tokens)
        for token in tf:
            tf[token] /= doc_len

        # Apply IDF weights (using pre-computed or default)
        vector: dict[str, float] = {}
        for token, freq in tf.items():
            idf = self._get_idf(token)
            vector[token] = freq * idf

        return Embedding(vector=vector, text=text, dimension=len(vector))

    def build_intent_embeddings(self, intents: dict[str, dict[str, Any]]) -> None:
        """Build embeddings for all intent descriptions.

        Args:
            intents: Dict mapping intent name to its metadata
                     (description, trigger_phrases, etc.)
        """
        t0 = time.time()
        self._document_count = 0
        self._document_frequency = {}

        # First pass: compute document frequencies
        all_docs: list[tuple[str, str]] = []
        for intent_name, meta in intents.items():
            doc_text = self._build_intent_document(intent_name, meta)
            all_docs.append((intent_name, doc_text))
            tokens = set(self._tokenize(doc_text))
            self._document_count += 1
            for token in tokens:
                self._document_frequency[token] = (
                    self._document_frequency.get(token, 0) + 1
                )

        # Second pass: build embeddings
        for intent_name, doc_text in all_docs:
            self._intent_embeddings[intent_name] = self.embed(doc_text)

        self._build_time = time.time() - t0

    def find_best_intent(
        self,
        text: str,
        threshold: float = 0.15,
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """Find the most semantically similar intent for the given text.

        Args:
            text: User input text.
            threshold: Minimum similarity score to consider.
            top_k: Number of top results to return.

        Returns:
            List of (intent_name, similarity_score) tuples,
            sorted by score descending.
        """
        if not self._intent_embeddings:
            return []

        query_embedding = self.embed(text)
        scores: list[tuple[str, float]] = []

        for intent_name, intent_emb in self._intent_embeddings.items():
            score = query_embedding.cosine_similarity(intent_emb)
            if score >= threshold:
                scores.append((intent_name, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute semantic similarity between two texts."""
        emb_a = self.embed(text_a)
        emb_b = self.embed(text_b)
        return emb_a.cosine_similarity(emb_b)

    def get_embedding_stats(self) -> dict[str, Any]:
        """Return embedding engine statistics."""
        return {
            "total_intents": len(self._intent_embeddings),
            "vocabulary_size": len(self._document_frequency),
            "document_count": self._document_count,
            "build_time_ms": self._build_time * 1000,
        }

    # ── Internal helpers ───────────────────────────────────────────

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize and normalize text."""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        tokens = text.split()
        return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]

    def _get_idf(self, token: str) -> float:
        """Get inverse document frequency for a token."""
        df = self._document_frequency.get(token, 0)
        if df == 0:
            return 1.0  # Unknown token gets neutral weight
        return math.log(self._document_count / df) + 1.0

    def _build_intent_document(
        self,
        intent_name: str,
        meta: dict[str, Any],
    ) -> str:
        """Build a descriptive document for an intent from its metadata."""
        parts = [intent_name.replace("_", " ").lower()]

        if "description" in meta:
            parts.append(meta["description"])
        if "trigger_phrases" in meta:
            parts.extend(meta["trigger_phrases"])
        if "examples" in meta:
            if isinstance(meta["examples"], list):
                parts.extend(meta["examples"])

        return " ".join(parts)


# ════════════════════════════════════════════════════════════════════
# SEMANTIC DOMAIN CLUSTERS
# ════════════════════════════════════════════════════════════════════

DOMAIN_CLUSTERS: dict[str, list[str]] = {
    "entertainment": [
        "watch something", "bored", "entertainment", "videos",
        "youtube", "netflix", "movies", "fun", "relax",
        "pass time", "something to do", "need music", "play music",
        "listen to", "podcast", "game", "gaming",
    ],
    "productivity": [
        "work", "task", "reminder", "note", "calendar",
        "meeting", "schedule", "deadline", "todo", "list",
        "organize", "plan", "project", "manage",
    ],
    "programming": [
        "code", "coding", "develop", "debug", "compile",
        "repository", "git", "python", "javascript", "vscode",
        "terminal", "programming", "software", "build", "test",
    ],
    "knowledge": [
        "learn", "research", "study", "understand", "explain",
        "information", "what is", "how to", "tutorial", "course",
        "paper", "article", "documentation", "docs",
    ],
    "system": [
        "volume", "brightness", "wifi", "bluetooth", "shutdown",
        "restart", "screenshot", "settings", "control", "power",
        "display", "sound", "network", "battery",
    ],
    "communication": [
        "email", "message", "call", "phone", "contact",
        "chat", "send", "reply", "forward", "share",
    ],
    "finance": [
        "stock", "price", "market", "invest", "crypto",
        "portfolio", "trade", "money", "budget", "expense",
    ],
    "health": [
        "exercise", "workout", "health", "sleep", "meditation",
        "diet", "nutrition", "fitness", "wellness", "stress",
    ],
}


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

semantic_engine = SemanticEmbeddingEngine()
