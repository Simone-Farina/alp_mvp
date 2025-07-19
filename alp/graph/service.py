from alp.graph.storage import load_graph_for_user
from alp.graph.model import KnowledgeGraph

def get_or_load_graph(user_id: str, cache: dict) -> KnowledgeGraph:
    """
    Retrieve KnowledgeGraph from a simple dict cache (e.g. st.session_state),
    loading from DB if not present.
    """
    key = f"kg_{user_id}"
    if key not in cache:
        cache[key] = load_graph_for_user(user_id)
    return cache[key]
