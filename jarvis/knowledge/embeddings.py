"""Embedding Engine — Vector embeddings for semantic search.

Provides embedding generation and storage for knowledge retrieval.
Uses a simple TF-IDF-style approach when no external embedding model is available.
"""

from __future__ import annotations

import re
import math
import logging
from typing import Any
from collections import Counter
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    text: str = ""
    embedding: list[float] = field(default_factory=list)
    dimension: int = 0
    model: str = ""


class EmbeddingEngine:
    """Generate and compare text embeddings.

    Supports:
    - TF-IDF-style embeddings (built-in, no dependencies)
    - Cosine similarity comparison
    - Batch embedding generation
    - Embedding storage and retrieval
    """

    def __init__(self, dimension: int = 128) -> None:
        self._dimension = dimension
        self._vocab: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._doc_count: int = 0
        self._embeddings: dict[str, list[float]] = {}

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        if not text.strip():
            return [0.0] * self._dimension

        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self._dimension

        # TF-IDF vector
        tf = Counter(tokens)
        total = len(tokens)
        vec = [0.0] * self._dimension

        for token, count in tf.items():
            idx = self._hash_token(token)
            tf_val = count / total
            idf_val = self._idf.get(token, 1.0)
            vec[idx] += tf_val * idf_val

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]

        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    def store_embedding(self, key: str, text: str) -> list[float]:
        """Generate and store an embedding."""
        embedding = self.embed(text)
        self._embeddings[key] = embedding
        self._update_idf(text)
        return embedding

    def get_stored(self, key: str) -> list[float] | None:
        return self._embeddings.get(key)

    def similarity(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two embeddings."""
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search_similar(
        self,
        query: list[float],
        top_k: int = 5,
        min_score: float = 0.1,
    ) -> list[tuple[str, float]]:
        """Find most similar stored embeddings."""
        results: list[tuple[str, float]] = []
        for key, emb in self._embeddings.items():
            score = self.similarity(query, emb)
            if score >= min_score:
                results.append((key, score))
        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def search_text(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Search stored embeddings by text query."""
        query_emb = self.embed(query)
        return self.search_similar(query_emb, top_k)

    def _tokenize(self, text: str) -> list[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        # Remove stopwords
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "and",
            "but", "or", "nor", "not", "so", "yet", "both", "either",
            "neither", "each", "every", "all", "any", "few", "more",
            "most", "other", "some", "such", "no", "only", "own", "same",
            "than", "too", "very", "just", "because", "if", "when",
            "where", "how", "what", "which", "who", "whom", "this",
            "that", "these", "those", "it", "its",
        }
        return [t for t in tokens if t not in stopwords and len(t) > 1]

    def _hash_token(self, token: str) -> int:
        h = hash(token)
        return abs(h) % self._dimension

    def _update_idf(self, text: str) -> None:
        self._doc_count += 1
        tokens = set(self._tokenize(text))
        for token in tokens:
            self._idf[token] = self._idf.get(token, 0) + 1
        # Convert to IDF values
        for token in self._idf:
            self._idf[token] = math.log(self._doc_count / self._idf[token]) + 1

    def get_stats(self) -> dict[str, Any]:
        return {
            "dimension": self._dimension,
            "vocab_size": len(self._vocab),
            "stored_embeddings": len(self._embeddings),
            "doc_count": self._doc_count,
        }


embedding_engine = EmbeddingEngine()

__all__ = ["EmbeddingEngine", "EmbeddingResult", "embedding_engine"]
