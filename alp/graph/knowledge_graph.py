from __future__ import annotations

from typing import Iterable, Optional, List, Dict

import networkx as nx

# Attribute keys for node data in the graph
KNOWN_ATTR = "known"
NAME_ATTR = "name"
CONTENT_ATTR = "content"


class KnowledgeGraph:
    """
    In-memory directed knowledge graph for a single user.
    Wraps a networkx.DiGraph; node IDs correspond to Concept IDs from the database.
    """

    def __init__(self) -> None:
        self.G: nx.DiGraph = nx.DiGraph()
        self.version: int = 0  # can be used to track modifications

    # ----------------- Graph Construction -----------------
    def clear(self) -> None:
        """Remove all nodes and edges from the graph."""
        self.G.clear()
        self.version += 1

    def add_concept(self, concept_id: int, name: str, known: bool, content: str | None = None) -> None:
        """Add a concept node to the graph (if not already present)."""
        self.G.add_node(
            concept_id,
            **{
                NAME_ATTR: name,
                KNOWN_ATTR: bool(known),
                CONTENT_ATTR: content,
            },
        )
        self.version += 1

    def add_edge(self, src_id: int, dst_id: int) -> None:
        """Add a directed edge from src -> dst in the graph (ignores self-loops or missing nodes)."""
        if src_id == dst_id:
            return
        if not (src_id in self.G and dst_id in self.G):
            # If either node is missing, skip adding this edge
            return
        self.G.add_edge(src_id, dst_id)
        self.version += 1

    # ----------------- Graph Queries -----------------
    def has_concept(self, concept_id: int) -> bool:
        """Check if a concept node with given ID exists in the graph."""
        return concept_id in self.G

    def concept_data(self, concept_id: int) -> dict:
        """Get the data dictionary for a concept node."""
        return self.G.nodes[concept_id]

    def mark_known(self, concept_id: int) -> None:
        """Mark a concept as known in the graph (if present)."""
        if concept_id in self.G:
            if not self.G.nodes[concept_id].get(KNOWN_ATTR):
                self.G.nodes[concept_id][KNOWN_ATTR] = True
                self.version += 1

    def is_known(self, concept_id: int) -> bool:
        """Return True if the concept is marked as known, False otherwise."""
        return bool(self.G.nodes.get(concept_id, {}).get(KNOWN_ATTR, False))

    def shortest_path(self, start_id: int, end_id: int) -> Optional[List[int]]:
        """
        Find a shortest path (list of concept IDs) from start_id to end_id.
        Tries directed path first; falls back to undirected if no directed path exists.
        Returns None if no path is found.
        """
        try:
            return nx.shortest_path(self.G, start_id, end_id)
        except nx.NetworkXNoPath:
            pass
        try:
            return nx.shortest_path(self.G.to_undirected(), start_id, end_id)
        except nx.NetworkXNoPath:
            return None

    def neighbors_out(self, concept_id: int) -> Iterable[int]:
        """Iterate over concept IDs that are direct children (outgoing edges) of the given concept."""
        return self.G.successors(concept_id)

    def neighbors_in(self, concept_id: int) -> Iterable[int]:
        """Iterate over concept IDs that are direct parents (incoming edges) of the given concept."""
        return self.G.predecessors(concept_id)

    # ----------------- Export for UI -----------------
    def to_cytoscape_elements(self, highlight_path: List[int] | None = None) -> List[Dict]:
        """
        Convert the graph into a list of elements (nodes and edges) formatted for CytoscapeJS.
        If highlight_path is provided, marks nodes/edges along that path for special styling.
        """
        highlight_edges: set[tuple[int, int]] = set()
        if highlight_path and len(highlight_path) > 1:
            for u, v in zip(highlight_path, highlight_path[1:]):
                if self.G.has_edge(u, v):
                    highlight_edges.add((u, v))
                elif self.G.has_edge(v, u):
                    highlight_edges.add((v, u))  # highlight undirected edge if path goes opposite direction

        # Layout the graph for visualization
        pos = nx.spring_layout(self.G, seed=42)

        def scale(point: tuple[float, float]) -> tuple[float, float]:
            # Scale and translate graph coordinates for nicer appearance
            return float(point[0]) * 500 + 300, float(point[1]) * 500 + 300

        elements: List[Dict] = []
        # Nodes
        for cid, data in self.G.nodes(data=True):
            x, y = scale(pos[cid])
            node_el = {
                "data": {
                    "id": str(cid),
                    "label": data.get(NAME_ATTR),
                    "known": str(data.get(KNOWN_ATTR, False))
                },
                "position": {"x": x, "y": y},
            }
            if highlight_path and cid in highlight_path:
                node_el["data"]["pathHighlight"] = "true"
            elements.append(node_el)
        # Edges
        for u, v in self.G.edges():
            edge_el = {"data": {"source": str(u), "target": str(v)}}
            if (u, v) in highlight_edges:
                edge_el["data"]["pathHighlight"] = "true"
            elements.append(edge_el)
        return elements

    def counts(self) -> Dict[str, int]:
        """Return counts of nodes, edges, and known nodes in the graph."""
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
            "known": sum(1 for _, d in self.G.nodes(data=True) if d.get(KNOWN_ATTR)),
        }
