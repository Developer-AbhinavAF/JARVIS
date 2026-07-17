"""RAG Pipeline — Retrieval-Augmented Generation.

User Query -> Intent Detection -> Knowledge Retrieval -> Memory Retrieval
-> Embedding Search -> Context Compression -> Reasoning -> Response

The AI should never rely solely on parametric knowledge.
"""

from __future__ import annotations

import logging
from typing import Any

from .graph import knowledge_graph, Entity
from .embeddings import embedding_engine
from .compression import context_compressor
from .ranking import knowledge_ranker, RankedKnowledge

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline.

    Query -> Retrieve -> Rank -> Compress -> Context
    """

    def __init__(self) -> None:
        self._query_count: int = 0

    def query(
        self,
        text: str,
        max_context_tokens: int = 2000,
        min_relevance: float = 0.2,
    ) -> dict[str, Any]:
        """Process a query through the RAG pipeline.

        Returns:
            {
                "context": str,          # Compressed context for LLM
                "sources": list[dict],   # Ranked sources used
                "entities": list[dict],  # Related entities found
                "confidence": float,     # Confidence in retrieval
            }
        """
        self._query_count += 1

        # 1. Embedding search
        embedding_results = self._embedding_search(text, top_k=10, min_score=min_relevance)

        # 2. Graph search
        graph_results = self._graph_search(text, top_k=5)

        # 3. Combine and rank
        all_contexts = []
        sources: list[dict] = []

        for key, score in embedding_results:
            entity = knowledge_graph.get_entity(key.replace("entity:", ""))
            if entity:
                ctx = f"{entity.name}: {entity.description}"
                all_contexts.append(ctx)
                sources.append({
                    "name": entity.name,
                    "type": entity.entity_type,
                    "score": score,
                    "source": entity.source,
                })

        for entity in graph_results:
            ctx = f"{entity.name}: {entity.description}"
            if ctx not in all_contexts:
                all_contexts.append(ctx)
                sources.append({
                    "name": entity.name,
                    "type": entity.entity_type,
                    "score": entity.importance,
                    "source": entity.source,
                })

        # 4. Compress context
        context = context_compressor.compress(
            all_contexts,
            query=text,
            max_tokens=max_context_tokens,
        )

        # 5. Calculate confidence
        confidence = 0.0
        if sources:
            confidence = sum(s["score"] for s in sources) / len(sources)
            confidence = min(1.0, confidence)

        return {
            "context": context,
            "sources": sources[:10],
            "entities": [s for s in sources[:5]],
            "confidence": round(confidence, 3),
        }

    def _embedding_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.2,
    ) -> list[tuple[str, float]]:
        """Search by embedding similarity."""
        query_emb = embedding_engine.embed(query)
        return embedding_engine.search_similar(query_emb, top_k, min_score)

    def _graph_search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[Entity]:
        """Search the knowledge graph."""
        return knowledge_graph.search_entities(query, limit=top_k)

    def has_relevant_knowledge(self, query: str, threshold: float = 0.3) -> bool:
        """Check if we have relevant knowledge for a query."""
        result = self.query(query, max_context_tokens=500)
        return result["confidence"] >= threshold

    def get_stats(self) -> dict[str, Any]:
        return {
            "query_count": self._query_count,
            "graph_entities": knowledge_graph.entity_count,
            "graph_relationships": knowledge_graph.relationship_count,
            "stored_embeddings": len(embedding_engine._embeddings),
        }


rag_pipeline = RAGPipeline()

__all__ = ["RAGPipeline", "rag_pipeline"]
