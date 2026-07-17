"""Knowledge API — Unified interface for all knowledge operations.

Every module should access knowledge through:
  search(), retrieve(), learn(), summarize(), compress(), rank(), connect(), forget()

No direct database access.
"""

from __future__ import annotations

import logging
from typing import Any

from .graph import knowledge_graph, Entity, Relationship
from .embeddings import embedding_engine
from .ingestion import ingestion_pipeline, IngestionResult
from .rag import rag_pipeline
from .compression import context_compressor
from .ranking import knowledge_ranker, RankedKnowledge
from .background import background_learner, LearningTask
from .organization import self_organizer

logger = logging.getLogger(__name__)


class KnowledgeEngine:
    """Unified knowledge interface for JARVIS.

    Provides: search, retrieve, learn, summarize, compress, rank, connect, forget
    """

    def __init__(self) -> None:
        self.graph = knowledge_graph
        self.embeddings = embedding_engine
        self.ingestion = ingestion_pipeline
        self.rag = rag_pipeline
        self.compression = context_compressor
        self.ranker = knowledge_ranker
        self.background = background_learner
        self.organizer = self_organizer

    # ── Search ─────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 10,
        source_type: str = "",
    ) -> list[dict[str, Any]]:
        """Search knowledge base by text query."""
        entities = self.graph.search_entities(query, limit=limit)
        return [e.to_dict() for e in entities]

    def search_semantic(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Semantic search using embeddings."""
        results = self.rag.query(query)
        return results.get("sources", [])[:limit]

    # ── Retrieve ───────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Retrieve relevant context for a query (RAG)."""
        return self.rag.query(query, max_context_tokens=max_tokens)

    def retrieve_entity(self, name: str) -> dict[str, Any] | None:
        """Retrieve a specific entity by name."""
        entity = self.graph.get_entity_by_name(name)
        if entity:
            entity.access_count += 1
            return entity.to_dict()
        return None

    # ── Learn ──────────────────────────────────────────────────────

    def learn(
        self,
        content: str,
        source_type: str = "text",
        source_name: str = "",
        background: bool = False,
    ) -> dict[str, Any]:
        """Learn new information."""
        if background:
            task = self.background.learn(content, source_type)
            return {"status": "learning", "task_id": task.task_id}

        result = self.ingestion.ingest_text(
            content,
            source_type=source_type,
            source_name=source_name,
        )
        return {
            "success": result.success,
            "entities": result.entities_created,
            "relationships": result.relationships_created,
            "chunks": result.chunks_processed,
            "latency_ms": result.latency_ms,
        }

    def learn_document(self, path: str) -> dict[str, Any]:
        """Learn from a document file."""
        from .sources.handlers import document_handler
        doc = document_handler.process(path)
        if not doc.success:
            return {"success": False, "error": doc.error}

        result = self.ingestion.ingest_chunks(
            doc.chunks,
            source_type="document",
            source_name=doc.title,
        )
        return {
            "success": result.success,
            "title": doc.title,
            "entities": result.entities_created,
            "chunks": result.chunks_processed,
        }

    def learn_url(self, url: str) -> dict[str, Any]:
        """Learn from a URL (YouTube, GitHub, or website)."""
        if "youtube.com" in url or "youtu.be" in url:
            from .sources.handlers import youtube_handler
            source = youtube_handler.process(url)
        elif "github.com" in url:
            from .sources.handlers import github_handler
            source = github_handler.process(url)
        else:
            from .sources.handlers import website_handler
            source = website_handler.process(url)

        if not source.success:
            return {"success": False, "error": source.error}

        result = self.ingestion.ingest_chunks(
            source.chunks,
            source_type=source.source_type,
            source_name=source.title,
        )
        return {
            "success": result.success,
            "title": source.title,
            "entities": result.entities_created,
        }

    # ── Summarize ──────────────────────────────────────────────────

    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """Summarize text content."""
        return self.compression.summarize(text, max_sentences)

    # ── Compress ───────────────────────────────────────────────────

    def compress(
        self,
        contexts: list[str],
        query: str = "",
        max_tokens: int = 2000,
    ) -> str:
        """Compress multiple contexts for LLM consumption."""
        return self.compression.compress(contexts, query, max_tokens)

    # ── Rank ───────────────────────────────────────────────────────

    def rank(
        self,
        candidates: list[dict[str, Any]],
        query: str = "",
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Rank knowledge pieces by relevance."""
        ranked = self.ranker.rank(candidates, query, top_k)
        return [r.to_dict() for r in ranked]

    # ── Connect ────────────────────────────────────────────────────

    def connect(
        self,
        entity_a: str,
        entity_b: str,
        relationship_type: str = "related_to",
    ) -> dict[str, Any]:
        """Create a relationship between two entities."""
        ea = self.graph.get_entity_by_name(entity_a)
        eb = self.graph.get_entity_by_name(entity_b)
        if not ea or not eb:
            return {"success": False, "error": "Entity not found"}

        rel = Relationship(
            source_id=ea.entity_id,
            target_id=eb.entity_id,
            relationship_type=relationship_type,
        )
        self.graph.add_relationship(rel)
        return {"success": True, "relationship": rel.to_dict()}

    # ── Forget ─────────────────────────────────────────────────────

    def forget(self, query: str) -> dict[str, int]:
        """Remove knowledge matching query."""
        entities = self.graph.search_entities(query, limit=100)
        removed = 0
        for entity in entities:
            if self.graph.remove_entity(entity.entity_id):
                removed += 1
        return {"removed": removed}

    # ── Maintenance ────────────────────────────────────────────────

    def maintain(self) -> dict[str, Any]:
        """Run self-maintenance."""
        return self.organizer.run_maintenance()

    # ── Stats ──────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "graph": self.graph.get_stats(),
            "embeddings": self.embeddings.get_stats(),
            "ingestion": self.ingestion.get_stats(),
            "rag": self.rag.get_stats(),
            "background": self.background.get_stats(),
            "organization": self.organizer.get_stats(),
        }


knowledge_engine = KnowledgeEngine()

__all__ = ["KnowledgeEngine", "knowledge_engine"]
