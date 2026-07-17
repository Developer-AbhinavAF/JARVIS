"""Ingestion Pipeline — Source -> Clean -> Extract -> Embed -> Store.

Every source follows:
  Read -> Clean -> Normalize -> Extract Entities -> Extract Relationships
  -> Generate Embeddings -> Store -> Index -> Connect

Knowledge should never remain isolated.
"""

from __future__ import annotations

import time
import re
import logging
from typing import Any
from dataclasses import dataclass, field

from .graph import Entity, Relationship, knowledge_graph
from .embeddings import embedding_engine
from .ranking import knowledge_ranker

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result from ingesting a source."""
    source: str = ""
    source_type: str = ""
    entities_created: int = 0
    relationships_created: int = 0
    chunks_processed: int = 0
    embedding_count: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: str = ""


class IngestionPipeline:
    """Process any source into connected knowledge.

    Supports:
    - Text content
    - Documents (PDF, DOCX, TXT, Markdown)
    - YouTube transcripts
    - GitHub repositories
    - Websites
    - Raw text
    """

    def __init__(self) -> None:
        self._ingestion_count: int = 0
        self._total_entities: int = 0
        self._total_relationships: int = 0

    def ingest_text(
        self,
        text: str,
        source_type: str = "text",
        source_name: str = "",
        metadata: dict | None = None,
    ) -> IngestionResult:
        """Ingest raw text content."""
        t0 = time.perf_counter()
        result = IngestionResult(source=source_name, source_type=source_type)

        try:
            # Clean
            cleaned = self._clean_text(text)

            # Chunk
            chunks = self._chunk_text(cleaned)
            result.chunks_processed = len(chunks)

            # Extract entities
            entities = self._extract_entities(chunks, source_type, source_name)
            result.entities_created = len(entities)

            # Extract relationships
            relationships = self._extract_relationships(entities)
            result.relationships_created = len(relationships)

            # Generate embeddings and store
            for entity in entities:
                if entity.name:
                    embedding = embedding_engine.store_embedding(
                        f"entity:{entity.entity_id}",
                        f"{entity.name} {entity.description}",
                    )
                    entity.embedding = embedding
                    result.embedding_count += 1

            # Store in graph
            for entity in entities:
                knowledge_graph.add_entity(entity)
            for rel in relationships:
                try:
                    knowledge_graph.add_relationship(rel)
                except ValueError:
                    pass

            self._ingestion_count += 1
            self._total_entities += result.entities_created
            self._total_relationships += result.relationships_created

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error("Ingestion failed: %s", e)

        result.latency_ms = (time.perf_counter() - t0) * 1000
        return result

    def ingest_chunks(
        self,
        chunks: list[str],
        source_type: str = "text",
        source_name: str = "",
    ) -> IngestionResult:
        """Ingest pre-chunked content."""
        text = "\n\n".join(chunks)
        return self.ingest_text(text, source_type, source_name)

    def _clean_text(self, text: str) -> str:
        """Remove noise and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return text.strip()

    def _chunk_text(self, text: str, max_chunk_size: int = 1000) -> list[str]:
        """Split text into manageable chunks."""
        if len(text) <= max_chunk_size:
            return [text] if text else []

        chunks: list[str] = []
        paragraphs = text.split("\n\n")
        current = ""

        for para in paragraphs:
            if len(current) + len(para) > max_chunk_size:
                if current:
                    chunks.append(current)
                current = para
            else:
                current = f"{current}\n\n{para}" if current else para

        if current:
            chunks.append(current)

        return chunks

    def _extract_entities(
        self,
        chunks: list[str],
        source_type: str,
        source_name: str,
    ) -> list[Entity]:
        """Extract entities from text chunks."""
        entities: list[Entity] = []
        seen_names: set[str] = set()

        for chunk in chunks:
            # Simple entity extraction: capitalized phrases, technical terms
            extracted = self._simple_entity_extraction(chunk)

            for name, etype in extracted:
                name_lower = name.lower()
                if name_lower in seen_names or len(name) < 2:
                    continue
                seen_names.add(name_lower)

                entity = Entity(
                    name=name,
                    entity_type=etype,
                    description=self._extract_description(chunk, name),
                    source=source_type,
                    properties={"source_name": source_name},
                    importance=self._estimate_importance(name, chunk),
                )
                entities.append(entity)

        return entities

    _STOP_WORDS = frozenset({
        "The", "This", "That", "These", "Those", "And", "But", "Or",
        "It", "Its", "They", "Them", "Their", "There", "Then", "When",
        "What", "Which", "Who", "Whom", "How", "Can", "May", "Was",
        "Were", "Been", "Being", "Have", "Has", "Had", "Do", "Does",
        "Did", "Will", "Would", "Could", "Should", "Shall", "Might",
        "Must", "Need", "Not", "Also", "Just", "Only", "Even", "Still",
        "Already", "Yet", "Always", "Never", "Often", "Sometimes",
    })

    def _simple_entity_extraction(self, text: str) -> list[tuple[str, str]]:
        """Simple rule-based entity extraction."""
        entities: list[tuple[str, str]] = []

        # CamelCase words (FastAPI, NodeJS, TypeScript, etc.)
        camel = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]*)+)\b', text)
        for name in camel:
            if name not in self._STOP_WORDS and len(name) >= 3:
                entities.append((name, "concept"))

        # All-caps short acronyms (AI, API, ML, NLP, etc.)
        acronyms = re.findall(r'\b([A-Z]{2,6})\b', text)
        for name in acronyms:
            if name not in ("THE", "AND", "FOR", "BUT", "NOT", "ARE", "WAS") and len(name) >= 2:
                entities.append((name, "concept"))

        # Standard capitalized words (Python, Django, etc.)
        caps = re.findall(r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*)\b', text)
        for cap in caps:
            if cap not in self._STOP_WORDS and len(cap) >= 3:
                entities.append((cap, "concept"))

        # Technical terms (with dots, like file.ext)
        tech = re.findall(r'\b([a-zA-Z]+\.[a-zA-Z]{2,4})\b', text)
        for t in tech:
            entities.append((t, "file"))

        # URLs
        urls = re.findall(r'https?://[^\s]+', text)
        for url in urls:
            entities.append((url[:100], "website"))

        # Code blocks
        code = re.findall(r'`([^`]+)`', text)
        for c in code:
            if len(c) < 50:
                entities.append((c, "code"))

        return entities

    def _extract_relationships(self, entities: list[Entity]) -> list[Relationship]:
        """Extract relationships between co-occurring entities."""
        relationships: list[Relationship] = []

        # Connect entities that appear in the same context
        for i, e1 in enumerate(entities):
            for e2 in entities[i+1:i+5]:  # Connect to next 4 entities
                rel_type = self._infer_relationship_type(e1, e2)
                rel = Relationship(
                    source_id=e1.entity_id,
                    target_id=e2.entity_id,
                    relationship_type=rel_type,
                    weight=0.7,
                )
                relationships.append(rel)

        return relationships

    def _infer_relationship_type(self, e1: Entity, e2: Entity) -> str:
        """Infer relationship type between two entities."""
        type_pair = (e1.entity_type, e2.entity_type)
        relationship_map = {
            ("concept", "concept"): "related_to",
            ("concept", "code"): "uses",
            ("concept", "website"): "references",
            ("code", "file"): "part_of",
            ("website", "concept"): "explains",
        }
        return relationship_map.get(type_pair, "related_to")

    def _extract_description(self, chunk: str, entity_name: str) -> str:
        """Extract description context around an entity mention."""
        idx = chunk.find(entity_name)
        if idx == -1:
            return ""
        start = max(0, idx - 100)
        end = min(len(chunk), idx + len(entity_name) + 100)
        return chunk[start:end].strip()

    def _estimate_importance(self, name: str, context: str) -> float:
        """Estimate entity importance."""
        score = 0.5
        # Mentioned early in text
        idx = context.find(name)
        if idx < 200:
            score += 0.1
        # Frequently mentioned
        count = context.lower().count(name.lower())
        score += min(0.2, count * 0.05)
        # Technical/importance keywords
        important = ["important", "key", "main", "primary", "critical"]
        if any(w in context.lower() for w in important):
            score += 0.1
        return min(1.0, score)

    def get_stats(self) -> dict[str, Any]:
        return {
            "ingestion_count": self._ingestion_count,
            "total_entities": self._total_entities,
            "total_relationships": self._total_relationships,
        }


ingestion_pipeline = IngestionPipeline()

__all__ = ["IngestionPipeline", "IngestionResult", "ingestion_pipeline"]
