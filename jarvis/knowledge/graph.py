"""Knowledge Graph — Entity and relationship storage with traversal.

Knowledge is a graph, not a list. Every entity becomes connected.

Entity Types:
  People, Places, Projects, Repositories, Frameworks, Languages,
  Companies, Libraries, Applications, Files, Documents, Websites,
  Videos, Courses, Books, Events, Tasks, Goals

Relationship Types:
  Created By, Uses, Depends On, Related To, Part Of, References,
  Derived From, Solved By, Explains, Belongs To, Improves, Connected To
"""

from __future__ import annotations

import time
import uuid
import logging
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class Entity:
    """A node in the knowledge graph."""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    entity_type: str = ""          # person, project, framework, etc.
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)
    importance: float = 0.5        # 0.0 - 1.0
    confidence: float = 0.8        # 0.0 - 1.0
    source: str = ""               # where this entity came from
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    tags: list[str] = field(default_factory=list)

    @property
    def recency_score(self) -> float:
        """How recently was this entity accessed."""
        age_hours = (time.time() - self.updated_at) / 3600
        return max(0.0, 1.0 - age_hours / (24 * 30))  # decays over 30 days

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "description": self.description,
            "importance": self.importance,
            "confidence": self.confidence,
            "source": self.source,
            "tags": self.tags,
            "access_count": self.access_count,
        }


@dataclass
class Relationship:
    """An edge in the knowledge graph."""
    relationship_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    source_id: str = ""
    target_id: str = ""
    relationship_type: str = ""    # uses, depends_on, related_to, etc.
    weight: float = 1.0            # strength of connection
    properties: dict[str, Any] = field(default_factory=dict)
    source: str = ""               # where this relationship came from
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "weight": self.weight,
        }


@dataclass
class GraphPath:
    """A path through the knowledge graph."""
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    total_weight: float = 0.0

    @property
    def length(self) -> int:
        return len(self.entities)


# ════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH
# ════════════════════════════════════════════════════════════════════

class KnowledgeGraph:
    """In-memory knowledge graph with entity/relationship storage and traversal.

    Supports:
    - Entity CRUD with type filtering
    - Relationship creation and traversal
    - BFS/DFS graph traversal
    - Subgraph extraction
    - Similarity-based entity lookup
    - Graph statistics
    """

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        self._entity_index: dict[str, set[str]] = defaultdict(set)   # type -> entity_ids
        self._name_index: dict[str, str] = {}                        # name_lower -> entity_id
        self._adjacency: dict[str, set[str]] = defaultdict(set)      # entity_id -> neighbor_ids
        self._edge_index: dict[str, list[str]] = defaultdict(list)   # entity_id -> relationship_ids

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def relationship_count(self) -> int:
        return len(self._relationships)

    # ── Entity Operations ──────────────────────────────────────────

    def add_entity(self, entity: Entity) -> Entity:
        """Add or update an entity in the graph."""
        existing = self._name_index.get(entity.name.lower())
        if existing and existing in self._entities:
            # Merge with existing
            old = self._entities[existing]
            old.properties.update(entity.properties)
            old.updated_at = time.time()
            if entity.description:
                old.description = entity.description
            if entity.embedding:
                old.embedding = entity.embedding
            return old

        self._entities[entity.entity_id] = entity
        self._entity_index[entity.entity_type].add(entity.entity_id)
        self._name_index[entity.name.lower()] = entity.entity_id
        return entity

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def get_entity_by_name(self, name: str) -> Entity | None:
        eid = self._name_index.get(name.lower())
        return self._entities.get(eid) if eid else None

    def find_entities(
        self,
        entity_type: str = "",
        tags: list[str] | None = None,
        min_importance: float = 0.0,
        limit: int = 50,
    ) -> list[Entity]:
        """Find entities by type, tags, or importance."""
        candidates: list[Entity] = []

        if entity_type:
            eids = self._entity_index.get(entity_type, set())
            candidates = [self._entities[eid] for eid in eids if eid in self._entities]
        else:
            candidates = list(self._entities.values())

        if tags:
            tag_set = set(tags)
            candidates = [e for e in candidates if tag_set.intersection(e.tags)]

        candidates = [e for e in candidates if e.importance >= min_importance]
        candidates.sort(key=lambda e: (-e.importance, -e.access_count))
        return candidates[:limit]

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and all its relationships."""
        entity = self._entities.pop(entity_id, None)
        if not entity:
            return False

        # Clean up indexes
        self._entity_index[entity.entity_type].discard(entity_id)
        self._name_index.pop(entity.name.lower(), None)
        self._adjacency.pop(entity_id, None)

        # Remove relationships
        rel_ids = list(self._edge_index.pop(entity_id, []))
        for rid in rel_ids:
            rel = self._relationships.pop(rid, None)
            if rel:
                self._adjacency[rel.source_id].discard(entity_id)
                self._adjacency[rel.target_id].discard(entity_id)

        return True

    def search_entities(self, query: str, limit: int = 10) -> list[Entity]:
        """Simple text search across entities."""
        query_lower = query.lower()
        results: list[tuple[Entity, float]] = []

        for entity in self._entities.values():
            score = 0.0
            if query_lower in entity.name.lower():
                score += 0.6
            if query_lower in entity.description.lower():
                score += 0.3
            if any(query_lower in tag.lower() for tag in entity.tags):
                score += 0.2
            if score > 0:
                results.append((entity, score))

        results.sort(key=lambda x: -x[1])
        return [e for e, _ in results[:limit]]

    # ── Relationship Operations ────────────────────────────────────

    def add_relationship(self, relationship: Relationship) -> Relationship:
        """Add a relationship between two entities."""
        if relationship.source_id not in self._entities:
            raise ValueError(f"Source entity not found: {relationship.source_id}")
        if relationship.target_id not in self._entities:
            raise ValueError(f"Target entity not found: {relationship.target_id}")

        self._relationships[relationship.relationship_id] = relationship
        self._adjacency[relationship.source_id].add(relationship.target_id)
        self._adjacency[relationship.target_id].add(relationship.source_id)
        self._edge_index[relationship.source_id].append(relationship.relationship_id)
        self._edge_index[relationship.target_id].append(relationship.relationship_id)
        return relationship

    def get_relationships(
        self,
        entity_id: str,
        relationship_type: str = "",
        direction: str = "both",  # outgoing, incoming, both
    ) -> list[Relationship]:
        """Get relationships for an entity."""
        results: list[Relationship] = []

        for rel in self._relationships.values():
            if direction == "outgoing" and rel.source_id != entity_id:
                continue
            if direction == "incoming" and rel.target_id != entity_id:
                continue
            if rel.source_id != entity_id and rel.target_id != entity_id:
                continue
            if relationship_type and rel.relationship_type != relationship_type:
                continue
            results.append(rel)

        return results

    # ── Graph Traversal ────────────────────────────────────────────

    def get_neighbors(
        self,
        entity_id: str,
        max_depth: int = 1,
    ) -> list[Entity]:
        """Get neighboring entities up to max_depth."""
        visited: set[str] = set()
        result: list[Entity] = []
        queue: list[tuple[str, int]] = [(entity_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)

            if current_id != entity_id:
                entity = self._entities.get(current_id)
                if entity:
                    result.append(entity)

            if depth < max_depth:
                for neighbor_id in self._adjacency.get(current_id, set()):
                    if neighbor_id not in visited:
                        queue.append((neighbor_id, depth + 1))

        return result

    def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 6,
    ) -> GraphPath | None:
        """BFS to find shortest path between two entities."""
        if start_id == end_id:
            entity = self._entities.get(start_id)
            return GraphPath(entities=[entity]) if entity else None

        visited: set[str] = {start_id}
        queue: list[tuple[str, list[str]]] = [(start_id, [start_id])]

        while queue:
            current_id, path = queue.pop(0)
            if len(path) > max_depth:
                continue

            for neighbor_id in self._adjacency.get(current_id, set()):
                if neighbor_id == end_id:
                    full_path = path + [neighbor_id]
                    entities = [self._entities[eid] for eid in full_path if eid in self._entities]
                    return GraphPath(entities=entities)

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return None

    def get_subgraph(
        self,
        center_id: str,
        max_depth: int = 2,
    ) -> tuple[list[Entity], list[Relationship]]:
        """Extract a subgraph centered on an entity."""
        neighbors = self.get_neighbors(center_id, max_depth)
        neighbor_ids = {e.entity_id for e in neighbors}
        neighbor_ids.add(center_id)

        entities = [self._entities[eid] for eid in neighbor_ids if eid in self._entities]
        relationships = [
            rel for rel in self._relationships.values()
            if rel.source_id in neighbor_ids and rel.target_id in neighbor_ids
        ]

        return entities, relationships

    # ── Similarity ─────────────────────────────────────────────────

    def find_similar(
        self,
        entity_id: str,
        limit: int = 5,
    ) -> list[tuple[Entity, float]]:
        """Find entities similar to a given entity (by embedding)."""
        source = self._entities.get(entity_id)
        if not source or not source.embedding:
            return []

        results: list[tuple[Entity, float]] = []
        for entity in self._entities.values():
            if entity.entity_id == entity_id or not entity.embedding:
                continue
            sim = self._cosine_similarity(source.embedding, entity.embedding)
            if sim > 0.3:
                results.append((entity, sim))

        results.sort(key=lambda x: -x[1])
        return results[:limit]

    def find_by_embedding(
        self,
        embedding: list[float],
        limit: int = 5,
        min_similarity: float = 0.3,
    ) -> list[tuple[Entity, float]]:
        """Find entities most similar to a query embedding."""
        results: list[tuple[Entity, float]] = []
        for entity in self._entities.values():
            if not entity.embedding:
                continue
            sim = self._cosine_similarity(embedding, entity.embedding)
            if sim >= min_similarity:
                results.append((entity, sim))

        results.sort(key=lambda x: -x[1])
        return results[:limit]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ── Maintenance ────────────────────────────────────────────────

    def merge_duplicates(self) -> int:
        """Find and merge duplicate entities (same name)."""
        merged = 0
        seen_names: dict[str, str] = {}

        for entity in list(self._entities.values()):
            name_lower = entity.name.lower()
            if name_lower in seen_names:
                # Merge into the first one
                primary = self._entities.get(seen_names[name_lower])
                if primary and primary.entity_id != entity.entity_id:
                    primary.properties.update(entity.properties)
                    primary.tags = list(set(primary.tags + entity.tags))
                    primary.access_count += entity.access_count
                    primary.updated_at = max(primary.updated_at, entity.updated_at)
                    self.remove_entity(entity.entity_id)
                    merged += 1
            else:
                seen_names[name_lower] = entity.entity_id

        return merged

    def get_stats(self) -> dict[str, Any]:
        return {
            "entity_count": self.entity_count,
            "relationship_count": self.relationship_count,
            "entity_types": {t: len(ids) for t, ids in self._entity_index.items()},
            "avg_importance": (
                sum(e.importance for e in self._entities.values()) / max(1, self.entity_count)
            ),
        }


# ════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════

knowledge_graph = KnowledgeGraph()

__all__ = [
    "Entity", "Relationship", "GraphPath",
    "KnowledgeGraph", "knowledge_graph",
]
