from __future__ import annotations

from typing import Optional, Tuple, List, Dict

from alp.ai.learning_plan import LearningPlan
from alp.db.models import Note, Concept, Edge
from alp.db.session import session_scope
from alp.graph.knowledge_graph import KnowledgeGraph
from alp.logging.config import get_logger
from alp.logging.instrumentation import traced

log = get_logger("graph.service")


class GraphService:
    """
    Service layer for managing knowledge graph operations (loading graph, adding concepts/notes, 
    updating known status, injecting learning plans).
    """

    @classmethod
    @traced("graph.load_graph")
    def load_graph(cls, user_id: str) -> KnowledgeGraph:
        """
        Load the knowledge graph for the given user from the database.
        Returns a KnowledgeGraph object containing all concepts and edges for that user.
        """
        log.debug("load_graph.start", user_id=user_id)
        graph = KnowledgeGraph()
        with session_scope() as db:
            # Load all concepts for the user
            concepts = db.query(Concept).filter(Concept.user_id == user_id).all()
            for concept in concepts:
                graph.add_concept(
                    concept_id=concept.id,
                    name=concept.name,
                    known=concept.is_known,
                    content=concept.content,
                )
            # Load all edges for the user
            edges = db.query(Edge).filter(Edge.user_id == user_id).all()
            for edge in edges:
                graph.add_edge(edge.source_id, edge.target_id)
        log.info("load_graph.done", nodes=graph.counts()["nodes"], edges=graph.counts()["edges"])
        return graph

    @classmethod
    @traced("graph.add_note")
    def add_note(cls, user_id: str, title: str, content: str, parent_name: Optional[str] = None) -> int:
        """
        Create a new Note and corresponding Concept (marked as known) for the user.
        If parent_name is provided, ensure a parent concept exists (or create it if not)
        and link it via an Edge to the new concept.
        Returns the concept ID of the newly created concept.
        """
        log.info("add_note.call", user_id=user_id, title=title, parent=parent_name)
        with session_scope() as db:
            # Create and save the Note
            note = Note(user_id=user_id, title=title, content=content)
            db.add(note)
            db.flush()  # flush to assign note.id if needed (not used further here)
            # Create the Concept linked to this note
            concept = Concept(user_id=user_id, name=title, content=content, is_known=True)
            db.add(concept)
            db.flush()  # assign concept.id
            if parent_name:
                # Find existing parent concept by name, or create if it doesn't exist
                parent = db.query(Concept).filter_by(user_id=user_id, name=parent_name).first()
                if not parent:
                    parent = Concept(user_id=user_id, name=parent_name, content=None, is_known=False)
                    db.add(parent)
                    db.flush()
                # Create an edge from parent -> new concept
                db.add(Edge(user_id=user_id, source_id=parent.id, target_id=concept.id))
            log.info("add_note.done", concept_id=concept.id)
            # Note: session_scope will commit on exit
            return concept.id

    @classmethod
    def mark_concept_known(cls, user_id: str, concept_id: int, graph: Optional[KnowledgeGraph] = None) -> None:
        """
        Mark the given concept as known in the database (and optionally in-memory graph).
        If a KnowledgeGraph object is provided, also update it in memory.
        """
        with session_scope() as db:
            concept = db.query(Concept).filter(Concept.user_id == user_id, Concept.id == concept_id).first()
            if concept and not concept.is_known:
                concept.is_known = True
        if graph:
            graph.mark_known(concept_id)

    @classmethod
    @traced("graph.inject_plan")
    def inject_plan(cls, user_id: str, graph: KnowledgeGraph, plan: LearningPlan,
                    depth: int, max_nodes: int) -> Tuple[int, int, List[str]]:
        """
        Integrate a generated LearningPlan into the user's knowledge graph and database.
        Filters the plan to the given depth and size, then adds any new concepts and edges.
        Returns a tuple (added_count, reused_count, skipped_prerequisites).
        """
        log.info("inject_plan.call", user_id=user_id, depth=depth, max_nodes=max_nodes,
                 plan_root=plan.root_topic, raw_nodes=len(plan.nodes))
        # Filter the plan nodes by depth and limit
        filtered_plan = plan.filtered(depth, max_nodes)
        # Map existing concept names (lowercase) to their IDs in the current graph
        existing_map: Dict[str, int] = {
            data.get("name").lower(): cid
            for cid, data in graph.G.nodes(data=True)
            if data.get("name")
        }
        added = 0
        reused = 0
        skipped_prereqs: set[str] = set()
        name_to_id: Dict[str, int] = {}
        with session_scope() as db:
            # 1. Add or reuse concepts from the plan
            for node in filtered_plan.nodes:
                lname = node.name.lower()
                if lname in existing_map:
                    cid = existing_map[lname]
                    reused += 1
                else:
                    # Create a new Concept for this plan node (mark as unknown/learning)
                    c = Concept(user_id=user_id, name=node.name, content=(node.summary or None), is_known=False)
                    db.add(c)
                    db.flush()
                    cid = c.id
                    # Add to graph in-memory
                    graph.add_concept(cid, node.name, False, node.summary or None)
                    added += 1
                    existing_map[lname] = cid
                name_to_id[node.name] = cid
            # 2. Add edges for prerequisites relationships
            for node in filtered_plan.nodes:
                tgt = name_to_id[node.name]
                for prereq_name in node.prerequisites:
                    lname = prereq_name.lower()
                    if lname not in existing_map:
                        skipped_prereqs.add(prereq_name)
                        continue
                    src = existing_map[lname]
                    if src == tgt:
                        continue
                    if not graph.G.has_edge(src, tgt):
                        db.add(Edge(user_id=user_id, source_id=src, target_id=tgt))
                        graph.add_edge(src, tgt)
        # Return counts and sorted list of any prerequisites that were missing (skipped)
        log.info("inject_plan.result", added=added, reused=reused, skipped=len(skipped_prereqs))
        return added, reused, sorted(skipped_prereqs)
