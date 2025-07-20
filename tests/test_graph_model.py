from alp.db.models import Concept, User, Edge
from alp.db.session import session_scope
from alp.graph.storage import load_graph_for_user


def _make_user():
    with session_scope() as db:
        u = User(name="Tester", learning_style="Visual")
        db.add(u)
        db.flush()  # ensures u.id populated before commit
        return u.id


def _add_concept(user_id: str, name: str, known: bool):
    with session_scope() as db:
        c = Concept(user_id=user_id, name=name, content=None, is_known=known)
        db.add(c)
        db.flush()
        return c.id


def _add_edge(user_id: str, src: int, dst: int):
    with session_scope() as db:
        e = Edge(user_id=user_id, source_id=src, target_id=dst)
        db.add(e)


def test_load_and_path():
    user_id = _make_user()
    a = _add_concept(user_id, "Math", True)
    b = _add_concept(user_id, "Calculus", False)
    c = _add_concept(user_id, "Limits", False)
    _add_edge(user_id, a, b)
    _add_edge(user_id, b, c)

    graph = load_graph_for_user(user_id)
    counts = graph.counts()
    assert counts["nodes"] == 3
    assert counts["edges"] == 2
    assert counts["known"] == 1

    path = graph.shortest_path(a, c)
    assert path == [a, b, c]


def test_mark_known():
    user_id = _make_user()
    a = _add_concept(user_id, "Algebra", False)
    graph = load_graph_for_user(user_id)
    assert not graph.is_known(a)
    graph.mark_known(a)
    assert graph.is_known(a)
