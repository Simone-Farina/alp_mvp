from alp.ai.learning_plan import LearningPlan, LearningPlanNode
from alp.graph import GraphService
from alp.user import UserService


def test_load_and_inject_plan():
    """Test loading a graph, adding a concept, and injecting a learning plan with new nodes and edges."""
    # Create a test user
    user = UserService.create_user(name="Tester", learning_style="Visual")
    user_id = user.id
    # Add a known concept "Math" via adding a note
    GraphService.add_note(user_id, title="Math", content="Basic Math content")
    # Verify the graph now has 1 known node and no edges
    graph1 = GraphService.load_graph(user_id)
    counts1 = graph1.counts()
    assert counts1["nodes"] == 1
    assert counts1["edges"] == 0
    assert counts1["known"] == 1  # "Math" is known
    # Prepare a LearningPlan with "Math" -> "Calculus" -> "Limits" dependency
    node_math = LearningPlanNode(name="Math", summary="", difficulty=1, prerequisites=[])
    node_calculus = LearningPlanNode(name="Calculus", summary="", difficulty=2, prerequisites=["Math"])
    node_limits = LearningPlanNode(name="Limits", summary="", difficulty=3, prerequisites=["Calculus"])
    plan = LearningPlan(root_topic="Math", nodes=[node_math, node_calculus, node_limits])
    # Inject the plan into the user's graph
    added, reused, skipped = GraphService.inject_plan(user_id, graph1, plan, depth=4, max_nodes=10)
    # After injection, the graph should have 3 nodes and 2 edges
    counts2 = graph1.counts()
    assert counts2["nodes"] == 3
    assert counts2["edges"] == 2
    # "Math" was reused (known), "Calculus" and "Limits" added as unknown
    assert counts2["known"] == 1
    # Verify the shortest path from Math to Limits is as expected
    math_id = next(cid for cid, data in graph1.G.nodes(data=True) if data["name"] == "Math")
    limits_id = next(cid for cid, data in graph1.G.nodes(data=True) if data["name"] == "Limits")
    calculus_id = next(cid for cid, data in graph1.G.nodes(data=True) if data["name"] == "Calculus")
    path = graph1.shortest_path(math_id, limits_id)
    assert path == [math_id, calculus_id, limits_id]
    # Check that reuse/skipped counts from inject_plan make sense
    assert added == 2  # Calculus, Limits added
    assert reused == 1  # Math reused
    assert skipped == []  # No missing prereqs (Math was present)


def test_mark_concept_known():
    """Test marking a concept as known updates both the graph and the database."""
    user = UserService.create_user(name="Tester2", learning_style="Analytical")
    user_id = user.id
    # Inject a plan with a single concept "Algebra" (unknown initially)
    node_alg = LearningPlanNode(name="Algebra", summary="", difficulty=1, prerequisites=[])
    plan = LearningPlan(root_topic="Algebra", nodes=[node_alg])
    graph = GraphService.load_graph(user_id)  # starts empty
    GraphService.inject_plan(user_id, graph, plan, depth=1, max_nodes=1)
    # After injection, "Algebra" should be present and marked unknown
    alg_id = next(cid for cid, data in graph.G.nodes(data=True) if data["name"] == "Algebra")
    assert not graph.is_known(alg_id)
    # Mark the concept as known
    GraphService.mark_concept_known(user_id, alg_id, graph=graph)
    # The in-memory graph should now show it as known
    assert graph.is_known(alg_id)
    # Reload the graph from DB to verify persistence
    graph2 = GraphService.load_graph(user_id)
    assert graph2.is_known(alg_id)
