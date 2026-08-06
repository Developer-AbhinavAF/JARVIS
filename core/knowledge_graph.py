"""core/knowledge_graph.py — Knowledge Graph Engine for JARVIS vNext++.

Stores and queries entity-relation-entity nodes for instant graph retrieval.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeGraphEngine:
    """Manages simple persistent entity graph."""

    def __init__(self, storage_dir: str = "memory"):
        self.storage_file = Path(storage_dir) / "knowledge_graph.json"
        self._graph: List[Dict[str, str]] = []
        self._load()

    def _load(self) -> None:
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self._graph = json.load(f)
            except Exception as e:
                logger.error(f"Error loading knowledge graph: {e}")
                self._graph = []
        else:
            self._graph = [
                {"subject": "User", "relation": "creator", "object": "Abhinav"},
                {"subject": "JARVIS", "relation": "role", "object": "AI OS"},
            ]
            self._save()

    def _save(self) -> None:
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self._graph, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving knowledge graph: {e}")

    def add_relation(self, subject: str, relation: str, obj: str) -> None:
        """Add triple to graph if not present."""
        triple = {"subject": subject.strip(), "relation": relation.strip(), "object": obj.strip()}
        if triple not in self._graph:
            self._graph.append(triple)
            self._save()

    def query(self, entity: str) -> List[Dict[str, str]]:
        """Find all relations connected to entity."""
        entity_lower = entity.lower().strip()
        results = []
        for item in self._graph:
            if entity_lower in item["subject"].lower() or entity_lower in item["object"].lower():
                results.append(item)
        return results

    def get_summary(self, entity: str) -> str:
        """Format relations as prompt text."""
        rels = self.query(entity)
        if not rels:
            return ""
        lines = [f"- {r['subject']} {r['relation']} {r['object']}" for r in rels[:5]]
        return "\n".join(lines)


knowledge_graph = KnowledgeGraphEngine()
