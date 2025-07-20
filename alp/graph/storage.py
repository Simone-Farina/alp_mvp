from __future__ import annotations

from alp.db.models import Concept, Edge
from alp.db.session import session_scope
from .model import KnowledgeGraph


def load_graph_for_user(user_id: str) -> KnowledgeGraph:
    """
    :param user_id: ID of user
    Load concepts + edges from DB into a KnowledgeGraph
    """
    graph = KnowledgeGraph()
    with session_scope() as db:
        concepts = (
            db.query(Concept)
            .filter(Concept.user_id == user_id)
            .all()
        )
        for concept in concepts:
            graph.add_concept(
                concept_id=concept.id,
                name=concept.name,
                known=concept.is_known,
                content=concept.content,
            )

        _edges = (
            db.query(Edge)
            .filter(Edge.user_id == user_id)
            .all()
        )
        for edge in _edges:
            graph.add_edge(edge.source_id, edge.target_id)

    return graph


def mark_known(user_id: str, concept_id: int) -> None:
    """
    :param user_id: ID of user
    :param concept_id: ID of concept
    Persist 'known' flag in DB.
    """
    with session_scope() as db:
        concept: Concept = (
            db.query(Concept)
            .filter(Concept.user_id == user_id, Concept.id == concept_id)
            .first()
        )
        if concept and not concept.is_known:
            concept.is_known = True
