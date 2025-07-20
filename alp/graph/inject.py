from __future__ import annotations
from typing import Dict, Tuple, List
from alp.db.session import session_scope
from alp.db.models import Concept, Edge
from alp.graph.model import KnowledgeGraph
from alp.core.learning_plan import LearningPlan

def inject_learning_plan(
    user_id: str,
    kg: KnowledgeGraph,
    plan: LearningPlan,
    depth: int,
    max_nodes: int
) -> Tuple[int, int, List[str]]:
    filtered = plan.filtered(depth, max_nodes)
    # existing names
    existing_map: Dict[str, int] = {
        data.get("name").lower(): cid
        for cid, data in kg.G.nodes(data=True)
        if data.get("name")
    }

    added = 0
    reused = 0
    skipped_prereqs: set[str] = set()
    name_to_id: Dict[str, int] = {}

    with session_scope() as db:
        # 1. concepts
        for node in filtered.nodes:
            lname = node.name.lower()
            if lname in existing_map:
                cid = existing_map[lname]
                reused += 1
            else:
                c = Concept(
                    user_id=user_id,
                    name=node.name,
                    content=node.get("summary") or None,
                    is_known=False
                )
                db.add(c)
                db.flush()
                cid = c.id
                existing_map[lname] = cid
                kg.add_concept(cid, node.name, False, node.get("summary"))
                added += 1
            name_to_id[node.name] = cid

        # 2. edges
        for node in filtered.nodes:
            tgt = name_to_id[node.name]
            for prereq_name in node.prerequisites:
                lname = prereq_name.lower()
                if lname not in existing_map:
                    skipped_prereqs.add(prereq_name)
                    continue
                src = existing_map[lname]
                if src == tgt:
                    continue
                if not kg.G.has_edge(src, tgt):
                    edge = Edge(user_id=user_id, source_id=src, target_id=tgt)
                    db.add(edge)
                    kg.add_edge(src, tgt)
    return added, reused, sorted(skipped_prereqs)
