"""Self-Organization — Periodic knowledge base maintenance.

The Knowledge Engine should periodically:
- Merge duplicates
- Compress memories
- Update relationships
- Remove noise
- Rebuild embeddings
- Optimize retrieval

Without user intervention.
"""

from __future__ import annotations

import time
import logging
from typing import Any

from .graph import knowledge_graph
from .embeddings import embedding_engine

logger = logging.getLogger(__name__)


class SelfOrganizer:
    """Periodic maintenance and optimization of the knowledge base."""

    def __init__(self) -> None:
        self._last_maintenance: float = 0.0
        self._maintenance_interval: float = 3600  # 1 hour
        self._maintenance_count: int = 0

    def should_maintain(self) -> bool:
        """Check if maintenance is due."""
        return (time.time() - self._last_maintenance) > self._maintenance_interval

    def run_maintenance(self) -> dict[str, Any]:
        """Run full maintenance cycle."""
        t0 = time.perf_counter()
        results: dict[str, Any] = {}

        # 1. Merge duplicates
        merged = knowledge_graph.merge_duplicates()
        results["merged_duplicates"] = merged

        # 2. Rebuild entity index (implicit in merge)
        results["entity_count"] = knowledge_graph.entity_count

        # 3. Remove low-importance noise
        removed = self._remove_noise()
        results["removed_noise"] = removed

        # 4. Update importance scores
        updated = self._update_importance()
        results["importance_updated"] = updated

        self._last_maintenance = time.time()
        self._maintenance_count += 1

        ms = (time.perf_counter() - t0) * 1000
        results["latency_ms"] = round(ms, 1)

        logger.info("Self-maintenance completed: %s", results)
        return results

    def _remove_noise(self) -> int:
        """Remove very low importance entities."""
        to_remove: list[str] = []
        for entity in knowledge_graph.find_entities(limit=1000):
            if entity.importance < 0.1 and entity.access_count == 0:
                age_days = (time.time() - entity.created_at) / 86400
                if age_days > 30:
                    to_remove.append(entity.entity_id)

        for eid in to_remove:
            knowledge_graph.remove_entity(eid)

        return len(to_remove)

    def _update_importance(self) -> int:
        """Update importance based on access patterns."""
        updated = 0
        for entity in knowledge_graph.find_entities(limit=1000):
            old = entity.importance
            # Boost frequently accessed
            if entity.access_count > 5:
                entity.importance = min(1.0, entity.importance + 0.05)
            # Decay very old, unaccessed
            age_days = (time.time() - entity.updated_at) / 86400
            if age_days > 90 and entity.access_count == 0:
                entity.importance = max(0.05, entity.importance - 0.05)
            if entity.importance != old:
                updated += 1
        return updated

    def get_stats(self) -> dict[str, Any]:
        return {
            "maintenance_count": self._maintenance_count,
            "last_maintenance": self._last_maintenance,
            "interval_seconds": self._maintenance_interval,
        }


self_organizer = SelfOrganizer()

__all__ = ["SelfOrganizer", "self_organizer"]
