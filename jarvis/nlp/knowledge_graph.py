"""Knowledge Graph for JARVIS NLP.

Store relationships between concepts.
Python → Language → Created By → Guido → Used In → AI → Backend → Automation
Everything becomes connected. This improves reasoning.
"""

from __future__ import annotations

import time
import json
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path


# ════════════════════════════════════════════════════════════════════
# GRAPH DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    id: str = ""
    label: str = ""
    node_type: str = ""  # concept, person, tool, language, project, etc.
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    importance: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "node_type": self.node_type,
            "properties": self.properties,
            "importance": round(self.importance, 3),
            "access_count": self.access_count,
        }


@dataclass
class GraphEdge:
    """A directed edge (relationship) in the knowledge graph."""
    source_id: str = ""
    target_id: str = ""
    relationship: str = ""  # created_by, used_in, is_a, has_property, etc.
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    access_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "relationship": self.relationship,
            "weight": round(self.weight, 3),
            "properties": self.properties,
        }


# ════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH
# ════════════════════════════════════════════════════════════════════

class KnowledgeGraph:
    """Stores relationships between concepts for improved reasoning.

    Supports:
    - Adding/querying nodes and edges
    - Traversal (BFS/DFS)
    - Relationship inference
    - Subgraph extraction
    - Persistence (JSON)
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._adjacency: dict[str, list[int]] = {}  # node_id → edge indices
        self._label_index: dict[str, str] = {}  # lowercase label → node_id
        self._type_index: dict[str, list[str]] = {}  # node_type → [node_ids]

    # ── Node operations ────────────────────────────────────────────

    def add_node(
        self,
        label: str,
        node_type: str = "concept",
        properties: dict[str, Any] | None = None,
        importance: float = 0.5,
    ) -> GraphNode:
        """Add a node to the graph. Returns existing node if label exists."""
        label_lower = label.lower()
        if label_lower in self._label_index:
            node_id = self._label_index[label_lower]
            node = self._nodes[node_id]
            node.access_count += 1
            return node

        node_id = f"n_{len(self._nodes)}"
        node = GraphNode(
            id=node_id,
            label=label,
            node_type=node_type,
            properties=properties or {},
            importance=importance,
        )

        self._nodes[node_id] = node
        self._label_index[label_lower] = node_id

        if node_type not in self._type_index:
            self._type_index[node_type] = []
        self._type_index[node_type].append(node_id)

        return node

    def get_node(self, label: str) -> GraphNode | None:
        """Get a node by label."""
        node_id = self._label_index.get(label.lower())
        if node_id:
            return self._nodes.get(node_id)
        return None

    def get_node_by_id(self, node_id: str) -> GraphNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def find_nodes_by_type(self, node_type: str) -> list[GraphNode]:
        """Find all nodes of a specific type."""
        node_ids = self._type_index.get(node_type, [])
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    # ── Edge operations ────────────────────────────────────────────

    def add_edge(
        self,
        source_label: str,
        target_label: str,
        relationship: str,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> GraphEdge | None:
        """Add a directed edge between two nodes.

        Creates nodes if they don't exist.
        """
        source = self.get_node(source_label)
        if not source:
            source = self.add_node(source_label)
        target = self.get_node(target_label)
        if not target:
            target = self.add_node(target_label)

        edge = GraphEdge(
            source_id=source.id,
            target_id=target.id,
            relationship=relationship,
            weight=weight,
            properties=properties or {},
        )

        self._edges.append(edge)
        edge_idx = len(self._edges) - 1

        if source.id not in self._adjacency:
            self._adjacency[source.id] = []
        self._adjacency[source.id].append(edge_idx)

        return edge

    def get_edges_from(self, label: str) -> list[GraphEdge]:
        """Get all outgoing edges from a node."""
        node = self.get_node(label)
        if not node:
            return []
        edge_indices = self._adjacency.get(node.id, [])
        return [self._edges[i] for i in edge_indices]

    def get_edges_to(self, label: str) -> list[GraphEdge]:
        """Get all incoming edges to a node."""
        node = self.get_node(label)
        if not node:
            return []
        return [e for e in self._edges if e.target_id == node.id]

    def get_neighbors(self, label: str, relationship: str | None = None) -> list[tuple[str, str]]:
        """Get neighboring nodes with their relationship labels.

        Returns list of (neighbor_label, relationship).
        """
        edges = self.get_edges_from(label)
        result = []
        for edge in edges:
            if relationship and edge.relationship != relationship:
                continue
            target = self._nodes.get(edge.target_id)
            if target:
                result.append((target.label, edge.relationship))
        return result

    # ── Traversal ──────────────────────────────────────────────────

    def traverse_bfs(
        self,
        start_label: str,
        max_depth: int = 3,
        relationship_filter: str | None = None,
    ) -> list[tuple[str, int]]:
        """Breadth-first traversal from a starting node.

        Returns list of (node_label, depth).
        """
        start = self.get_node(start_label)
        if not start:
            return []

        visited: set[str] = {start.id}
        queue: list[tuple[str, int]] = [(start_label, 0)]
        result: list[tuple[str, int]] = [(start_label, 0)]

        while queue:
            current_label, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            edges = self.get_edges_from(current_label)
            for edge in edges:
                if relationship_filter and edge.relationship != relationship_filter:
                    continue
                target = self._nodes.get(edge.target_id)
                if target and target.id not in visited:
                    visited.add(target.id)
                    result.append((target.label, depth + 1))
                    queue.append((target.label, depth + 1))

        return result

    def find_path(
        self,
        start_label: str,
        end_label: str,
        max_depth: int = 5,
    ) -> list[str] | None:
        """Find a path between two nodes using BFS.

        Returns list of node labels forming the path, or None.
        """
        start = self.get_node(start_label)
        end = self.get_node(end_label)
        if not start or not end:
            return None

        visited: set[str] = {start.id}
        queue: list[tuple[str, list[str]]] = [(start_label, [start_label])]

        while queue:
            current_label, path = queue.pop(0)
            if len(path) > max_depth:
                continue

            edges = self.get_edges_from(current_label)
            for edge in edges:
                target = self._nodes.get(edge.target_id)
                if not target:
                    continue
                if target.id == end.id:
                    return path + [target.label]
                if target.id not in visited:
                    visited.add(target.id)
                    queue.append((target.label, path + [target.label]))

        return None

    def get_related_concepts(
        self,
        label: str,
        depth: int = 2,
    ) -> list[tuple[str, str, int]]:
        """Get all concepts related to a given concept.

        Returns list of (related_label, relationship, depth).
        """
        results: list[tuple[str, str, int]] = []
        visited: set[str] = set()

        def _traverse(current_label: str, current_depth: int) -> None:
            if current_depth > depth:
                return
            edges = self.get_edges_from(current_label)
            for edge in edges:
                target = self._nodes.get(edge.target_id)
                if target and target.id not in visited:
                    visited.add(target.id)
                    results.append((target.label, edge.relationship, current_depth))
                    _traverse(target.label, current_depth + 1)

        _traverse(label, 1)
        return results

    # ── Persistence ────────────────────────────────────────────────

    def save(self, filepath: str | Path) -> None:
        """Save the knowledge graph to JSON."""
        data = {
            "nodes": {nid: node.to_dict() for nid, node in self._nodes.items()},
            "edges": [edge.to_dict() for edge in self._edges],
        }
        Path(filepath).write_text(json.dumps(data, indent=2, default=str))

    def load(self, filepath: str | Path) -> None:
        """Load the knowledge graph from JSON."""
        path = Path(filepath)
        if not path.exists():
            return

        data = json.loads(path.read_text())
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._label_index.clear()
        self._type_index.clear()

        for nid, node_data in data.get("nodes", {}).items():
            node = GraphNode(**node_data)
            self._nodes[nid] = node
            self._label_index[node.label.lower()] = nid
            if node.node_type not in self._type_index:
                self._type_index[node.node_type] = []
            self._type_index[node.node_type].append(nid)

        for edge_data in data.get("edges", []):
            edge = GraphEdge(**edge_data)
            self._edges.append(edge)
            edge_idx = len(self._edges) - 1
            if edge.source_id not in self._adjacency:
                self._adjacency[edge.source_id] = []
            self._adjacency[edge.source_id].append(edge_idx)

    # ── Stats ──────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return graph statistics."""
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": {t: len(ids) for t, ids in self._type_index.items()},
            "avg_importance": (
                sum(n.importance for n in self._nodes.values()) / len(self._nodes)
                if self._nodes else 0
            ),
        }


# ════════════════════════════════════════════════════════════════════
# BUILT-IN KNOWLEDGE
# ════════════════════════════════════════════════════════════════════

def bootstrap_knowledge(graph: KnowledgeGraph) -> None:
    """Pre-populate the knowledge graph with common relationships."""

    # Programming languages
    graph.add_edge("Python", "Programming Language", "is_a")
    graph.add_edge("Python", "Guido van Rossum", "created_by")
    graph.add_edge("Python", "AI", "used_in")
    graph.add_edge("Python", "Backend", "used_in")
    graph.add_edge("Python", "Automation", "used_in")
    graph.add_edge("Python", "Data Science", "used_in")

    graph.add_edge("JavaScript", "Programming Language", "is_a")
    graph.add_edge("JavaScript", "Web", "used_in")
    graph.add_edge("JavaScript", "Frontend", "used_in")
    graph.add_edge("JavaScript", "Node.js", "runtime")

    graph.add_edge("TypeScript", "Programming Language", "is_a")
    graph.add_edge("TypeScript", "JavaScript", "extends")
    graph.add_edge("TypeScript", "Type Safety", "provides")

    # Tools
    graph.add_edge("VS Code", "Code Editor", "is_a")
    graph.add_edge("VS Code", "Python", "supports")
    graph.add_edge("VS Code", "JavaScript", "supports")
    graph.add_edge("VS Code", "Extensions", "has_feature")

    graph.add_edge("GitHub", "Version Control", "is_a")
    graph.add_edge("GitHub", "Git", "uses")
    graph.add_edge("GitHub", "Collaboration", "enables")

    graph.add_edge("YouTube", "Video Platform", "is_a")
    graph.add_edge("YouTube", "Entertainment", "used_for")
    graph.add_edge("YouTube", "Learning", "used_for")

    graph.add_edge("Spotify", "Music Platform", "is_a")
    graph.add_edge("Spotify", "Music", "streams")
    graph.add_edge("Spotify", "Podcasts", "streams")

    # Frameworks
    graph.add_edge("FastAPI", "Python", "written_in")
    graph.add_edge("FastAPI", "Web Framework", "is_a")
    graph.add_edge("FastAPI", "REST API", "creates")
    graph.add_edge("FastAPI", "Async", "supports")

    graph.add_edge("React", "JavaScript", "written_in")
    graph.add_edge("React", "UI Library", "is_a")
    graph.add_edge("React", "Frontend", "used_for")

    # Concepts
    graph.add_edge("Machine Learning", "AI", "subset_of")
    graph.add_edge("Deep Learning", "Machine Learning", "subset_of")
    graph.add_edge("NLP", "Machine Learning", "subset_of")
    graph.add_edge("Computer Vision", "Machine Learning", "subset_of")

    graph.add_edge("API", "Software", "part_of")
    graph.add_edge("REST", "API", "type_of")
    graph.add_edge("GraphQL", "API", "type_of")

    # User concepts (will be expanded by learning)
    graph.add_edge("JARVIS", "AI Assistant", "is_a")
    graph.add_edge("JARVIS", "Python", "built_with")
    graph.add_edge("JARVIS", "NLP", "uses")
    graph.add_edge("JARVIS", "Operating System", "functions_as")


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

knowledge_graph = KnowledgeGraph()
bootstrap_knowledge(knowledge_graph)
