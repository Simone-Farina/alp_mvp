from alp.graph.model import KnowledgeGraph
from alp.graph.inject import inject_learning_plan
from alp.core.learning_plan import LearningPlan, LearningPlanNode
from alp.db.session import session_scope
from alp.db.models import User

def _user():
    with session_scope() as db:
        u = User(name="Tester", learning_style="Visual")
        db.add(u); db.flush()
        return u.id

def test_inject_learning_plan_basic():
    user_id = _user()
    kg = KnowledgeGraph()
    plan = LearningPlan(
        root_topic="Recursion",
        nodes=[
            LearningPlanNode(name="Recursion Basics", summary="Intro", difficulty=1, prerequisites=[]),
            LearningPlanNode(name="Call Stack", summary="Frames", difficulty=2, prerequisites=["Recursion Basics"]),
            LearningPlanNode(name="Tail Recursion", summary="Variant", difficulty=3, prerequisites=["Call Stack"]),
        ]
    )
    added, reused, skipped = inject_learning_plan(user_id, kg, plan, depth=3, max_nodes=10)
    assert added == 3
    assert reused == 0
    assert skipped == []
    # edges
    assert kg.shortest_path(
        next(cid for cid, d in kg.G.nodes(data=True) if d["name"] == "Recursion Basics"),
        next(cid for cid, d in kg.G.nodes(data=True) if d["name"] == "Tail Recursion"),
    ) is not None
