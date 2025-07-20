from __future__ import annotations

from typing import Iterable

import networkx as nx

# Public constants (styling keys later)
KNOWN_ATTR = "known"
NAME_ATTR = "name"
CONTENT_ATTR = "content"


class KnowledgeGraph:
    """
    In-memory directed knowledge graph for a single user.
    Wraps a networkx.DiGraph; node ids match DB concept ids (ints).
    """

    def __init__(self) -> None:
        self.G: nx.DiGraph = nx.DiGraph()
        self.version: int = 0  # increment on any mutation

    # ------------------------------------------------------------------
    # Loading / building
    # ------------------------------------------------------------------
    def clear(self) -> None:
        self.G.clear()
        # IDEA: use a decorator for all functions that increment version
        self.version += 1

    def add_concept(
            self,
            concept_id: int,
            name: str,
            known: bool,
            content: str | None = None,
    ) -> None:
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
        # Avoid accidental self-loops unless explicitly desired
        if src_id == dst_id:
            return
        if not (src_id in self.G and dst_id in self.G):
            # IDEA: silently ignore or raise? For MVP: ignore
            return
        self.G.add_edge(src_id, dst_id)
        self.version += 1

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def has_concept(self, concept_id: int) -> bool:
        return concept_id in self.G

    def concept_data(self, concept_id: int) -> dict:
        return self.G.nodes[concept_id]

    def mark_known(self, concept_id: int) -> None:
        if concept_id in self.G:
            if not self.G.nodes[concept_id].get(KNOWN_ATTR):
                self.G.nodes[concept_id][KNOWN_ATTR] = True
                self.version += 1

    def is_known(self, concept_id: int) -> bool:
        return bool(self.G.nodes[concept_id].get(KNOWN_ATTR, False))

    def shortest_path(self, a: int, b: int) -> list[int] | None:
        """
        Try directed path first; fallback to undirected if needed.
        """
        try:
            return nx.shortest_path(self.G, a, b)
        except nx.NetworkXNoPath:
            pass
        try:
            return nx.shortest_path(self.G.to_undirected(), a, b)
        except nx.NetworkXNoPath:
            return None

    def neighbors_out(self, concept_id: int) -> Iterable[int]:
        return self.G.successors(concept_id)

    def neighbors_in(self, concept_id: int) -> Iterable[int]:
        return self.G.predecessors(concept_id)

    # ------------------------------------------------------------------
    # Export (for frontend)
    # ------------------------------------------------------------------
    def to_cytoscape_elements(self, highlight_path: list[int] | None = None) -> list[dict]:
        highlight_edges: set[tuple[int, int]] = set()
        if highlight_path and len(highlight_path) > 1:
            for u, v in zip(highlight_path, highlight_path[1:]):
                if self.G.has_edge(u, v):
                    highlight_edges.add((u, v))
                elif self.G.has_edge(v, u):
                    highlight_edges.add((v, u))  # undirected fallback

        # ----- POSITION CALCULATION -----
        pos = nx.spring_layout(self.G, seed=42)

        # Scale & shift to nicer canvas coordinates
        def scale(p):
            return float(p[0]) * 500 + 300, float(p[1]) * 500 + 300

        elements: list[dict] = []
        for cid, data in self.G.nodes(data=True):
            x, y = scale(pos[cid])
            node_el = {
                "data": {
                    "id": str(cid),
                    "label": data.get("name"),
                    "known": str(data.get("known", False)),
                },
                "position": {"x": x, "y": y},
            }
            if highlight_path and cid in highlight_path:
                node_el["data"]["pathHighlight"] = "true"
            elements.append(node_el)

        for u, v in self.G.edges():
            edge_el = {"data": {"source": str(u), "target": str(v)}}
            if (u, v) in highlight_edges:
                edge_el["data"]["pathHighlight"] = "true"
            elements.append(edge_el)

        return elements

    # ------------------------------------------------------------------
    # Debug / counts
    # ------------------------------------------------------------------
    def counts(self) -> dict:
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
            "known": sum(1 for _, d in self.G.nodes(data=True) if d.get(KNOWN_ATTR)),
        }
