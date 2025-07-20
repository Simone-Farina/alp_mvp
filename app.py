import streamlit as st
from dotenv import load_dotenv

from alp.ai.service import OpenAIService
from alp.graph import GraphService
from alp.logging.config import configure_logging, get_logger
from alp.logging.instrumentation import init_tracing
from alp.user import UserService

configure_logging()
init_tracing()
log = get_logger("streamlit-app")

# ---------------------------------------------------------------------------
# Initialize environment and services
# ---------------------------------------------------------------------------
load_dotenv(".env")
# Instantiate AI service (e.g., OpenAI integration)
ai_service = OpenAIService()
# Load current user (for simplicity, use the first user in DB)
user = UserService.get_first_user()

# ---------------------------------------------------------------------------
# Navigation Sidebar
# ---------------------------------------------------------------------------
PAGE = st.sidebar.selectbox("Navigate", ["Dashboard", "Add Note", "Graph", "Learn"])
log.info("app.start", page=PAGE)


# ---------------------------------------------------------------------------
# Helper function for computing path highlight
# ---------------------------------------------------------------------------
def _compute_highlight_path(kg, start_id, end_id):
    if start_id is None or end_id is None:
        return None
    if start_id == end_id:
        return [start_id]
    return kg.shortest_path(start_id, end_id)


# Helper to trigger Streamlit rerun
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# ---------------------------------------------------------------------------
# Onboarding (if no user exists)
# ---------------------------------------------------------------------------
if user is None:
    st.subheader("Onboarding – Discover your learning style")
    name = st.text_input("Your name", "")
    q1 = st.selectbox(
        "When learning something new, what do you prefer?",
        [
            "Watching diagrams/videos",
            "Listening to explanations",
            "Hands‑on practice",
            "Reading detailed text",
        ],
    )
    q2 = st.selectbox(
        "Which sounds more appealing?",
        [
            "A colourful mind‑map",
            "An engaging podcast",
            "Building a prototype",
            "Reading a research paper",
        ],
    )
    if st.button("Submit"):
        if not name:
            st.error("Please enter your name.")
        else:
            answers = {"Q1": q1, "Q2": q2}
            # Create new user via onboarding service (this determines learning style using AI)
            new_user = UserService.onboard_user(name=name, answers=answers, ai_service=ai_service)
            st.success(f"Onboarding complete! Detected style: **{new_user.learning_style}**. Reload to continue.")
            st.stop()
    # Stop here until user is created
    st.stop()

# If we reach here, `user` exists
st.sidebar.markdown(f"**User:** {user.name}  \nStyle: *{user.learning_style}*")

# Initialize session state caches if not present
if "kg_cache" not in st.session_state:
    st.session_state["kg_cache"] = {}
if "graph_ui" not in st.session_state:
    st.session_state["graph_ui"] = {
        "mode": "explore",  # 'explore' or 'path' mode for graph interaction
        "path_start": None,
        "path_end": None,
        "last_selected": None,
    }
ui_state = st.session_state["graph_ui"]

# ---------------------------------------------------------------------------
# Dashboard Page
# ---------------------------------------------------------------------------
if PAGE == "Dashboard":
    st.header("Your Dashboard")
    st.write("Use **Add Note** to create concepts or **Graph** to explore your knowledge graph.")

# ---------------------------------------------------------------------------
# Add Note Page
# ---------------------------------------------------------------------------
elif PAGE == "Add Note":
    st.header("Add a new Note")
    title = st.text_input("Title / Topic")
    content = st.text_area("Markdown Content", height=220)
    parent = st.text_input("Optional broader topic this fits under (leave blank for root)")
    use_ai = st.checkbox("Let AI suggest parent topic")
    # If AI suggestion is requested and title/content provided
    if use_ai and title and content:
        with st.spinner("Asking AI..."):
            suggestion = ai_service.suggest_parent_topic(title, content)
        if suggestion:
            parent = suggestion
            st.success(f"AI suggests: **{parent}**")
        else:
            st.info("AI found no broader parent (will be a root concept).")
    if st.button("Save Note"):
        if not title or not content:
            st.error("Title and content are required.")
        else:
            # Add the new note and concept to the knowledge graph (and DB)
            GraphService.add_note(user.id, title, content, parent or None)
            # Invalidate cached graph so the new concept will appear on next load
            cache_key = f"kg_{user.id}"
            st.session_state["kg_cache"].pop(cache_key, None)
            st.success(f"Note '{title}' saved and added to your graph!")

# ---------------------------------------------------------------------------
# Learn Page (Generate Learning Path)
# ---------------------------------------------------------------------------
elif PAGE == "Learn":
    st.header("Generate Learning Path")
    topic = st.text_input("Target Topic", placeholder="e.g. Recursion")
    depth = st.slider("Depth (1 = overview, 4 = deep)", 1, 4, 2)
    max_nodes = st.number_input("Max nodes", min_value=3, max_value=30, value=10, step=1)
    if st.button("Generate Path"):
        if not topic.strip():
            st.error("Please enter a topic.")
        else:
            # Load or retrieve cached knowledge graph
            cache_key = f"kg_{user.id}"
            if cache_key not in st.session_state["kg_cache"]:
                st.session_state["kg_cache"][cache_key] = GraphService.load_graph(user.id)
            kg = st.session_state["kg_cache"][cache_key]
            # Get a sample of known concept names to provide context to the AI (limit to 25 to constrain prompt size)
            known_names = [data.get("name") for _, data in kg.G.nodes(data=True) if data.get("known")]
            known_sample = known_names[:25]
            with st.spinner("Calling AI..."):
                plan = ai_service.generate_learning_plan(topic, depth, user.learning_style or "", max_nodes,
                                                         known_sample)
            if not plan:
                st.error("Failed to generate a learning plan (check API key or content parsing).")
            else:
                added, reused, skipped = GraphService.inject_plan(user.id, kg, plan, depth, max_nodes)
                # If there's an elements cache for the graph visualization, clear it (optional cache for performance)
                if "elements_cache" in st.session_state:
                    st.session_state["elements_cache"].clear()
                st.success(f"Integrated plan: {added} new, {reused} reused nodes added to your graph.")
                if skipped:
                    st.info(f"Skipped unknown prerequisites (not added): {', '.join(skipped)}")
                # Display a summary of the injected nodes (filtered by depth/max_nodes)
                filtered_plan = plan.filtered(depth, max_nodes)
                st.markdown("### Injected Nodes (Filtered View)")
                for node in filtered_plan.nodes:
                    summary_snippet = (node.summary or "")[:200]
                    st.markdown(f"- **{node.name}** (d{node.difficulty}): {summary_snippet}")
                st.markdown("Go to the **Graph** page to view the new nodes in your knowledge graph.")

# ---------------------------------------------------------------------------
# Graph Page (Knowledge Graph Visualization)
# ---------------------------------------------------------------------------
elif PAGE == "Graph":
    st.header("Knowledge Graph")
    from streamlit_cytoscapejs import st_cytoscapejs

    # Load or cache the KnowledgeGraph for the user
    cache_key = f"kg_{user.id}"
    if cache_key not in st.session_state["kg_cache"]:
        st.session_state["kg_cache"][cache_key] = GraphService.load_graph(user.id)
    kg = st.session_state["kg_cache"][cache_key]

    # Top control bar: reload, mode toggle, reset path, stats
    col_reload, col_mode, col_reset, col_stats = st.columns([1, 1.3, 1.2, 3])
    with col_reload:
        if st.button("↻ Reload"):
            # Clear cached graph and reset any selected nodes
            st.session_state["kg_cache"].pop(cache_key, None)
            ui_state["path_start"] = None
            ui_state["path_end"] = None
            _rerun()
    with col_mode:
        if ui_state["mode"] == "explore":
            if st.button("Enter Path Mode"):
                ui_state["mode"] = "path"
                ui_state["path_start"] = None
                ui_state["path_end"] = None
                _rerun()
        else:
            if st.button("Exit Path Mode"):
                ui_state["mode"] = "explore"
                ui_state["path_start"] = None
                ui_state["path_end"] = None
                _rerun()
    with col_reset:
        if st.button("Reset Path", disabled=(ui_state["path_start"] is None and ui_state["path_end"] is None)):
            ui_state["path_start"] = None
            ui_state["path_end"] = None
            _rerun()
    with col_stats:
        counts = kg.counts()
        st.caption(
            f"Nodes: {counts['nodes']} | Known: {counts['known']} | Edges: {counts['edges']} | Mode: {ui_state['mode']}")

    # Compute any highlight path for path mode (before drawing graph)
    highlight_path = _compute_highlight_path(kg, ui_state["path_start"], ui_state["path_end"])

    # Define Cytoscape.js stylesheet for node/edge styling
    stylesheet = [
        {"selector": "node", "style": {
            "label": "data(label)", "font-size": "10px", "text-valign": "center",
            "color": "#222", "background-color": "#bdc3c7",
            "width": "26px", "height": "26px", "border-width": "2px", "border-color": "#ecf0f1"
        }},
        {"selector": "node[known = 'True']", "style": {
            "background-color": "#27ae60", "border-color": "#145a32",
            "font-weight": "600", "color": "#fff"
        }},
        {"selector": "node[pathHighlight = 'true']", "style": {
            "border-color": "#f39c12", "border-width": "4px",
            "background-color": "#d35400", "color": "#fff"
        }},
        {"selector": "edge", "style": {
            "curve-style": "bezier", "target-arrow-shape": "triangle",
            "target-arrow-color": "#7f8c8d", "line-color": "#7f8c8d",
            "width": 2, "arrow-scale": 1
        }},
        {"selector": "edge[pathHighlight = 'true']", "style": {
            "line-color": "#f39c12", "target-arrow-color": "#f39c12",
            "width": 4
        }},
    ]

    # Build graph elements for visualization (highlighting any path if applicable)
    elements = kg.to_cytoscape_elements(highlight_path=highlight_path)
    # Render interactive graph
    selected_payload = st_cytoscapejs(
        elements=elements,
        stylesheet=stylesheet,
        width=800,
        height=600,
        key="cytograph",
    )

    # Determine if a node was selected in the graph
    selected_id = None
    if selected_payload and isinstance(selected_payload, dict):
        raw_sid = selected_payload.get("selected_node_id")
        if raw_sid is not None:
            try:
                selected_id = int(raw_sid)
            except ValueError:
                selected_id = None

    # Path mode selection handling
    if ui_state["mode"] == "path" and selected_id is not None:
        # Only take action if selection changed since last interaction
        if ui_state["last_selected"] != selected_id:
            if ui_state["path_start"] is None:
                ui_state["path_start"] = selected_id
                st.toast("Start node set.")
            elif ui_state["path_end"] is None and selected_id != ui_state["path_start"]:
                ui_state["path_end"] = selected_id
                st.toast("End node set.")
            elif selected_id == ui_state["path_start"]:
                # If user clicks the start node again, clear the path selection
                ui_state["path_start"] = None
                ui_state["path_end"] = None
                st.toast("Path selection cleared.")
            elif selected_id != ui_state["path_end"]:
                # Update the end node if a different node (not the start) is selected
                ui_state["path_end"] = selected_id
                st.toast("End node updated.")
            ui_state["last_selected"] = selected_id
            _rerun()

    # Path summary and bulk action
    if highlight_path:
        # Calculate progress along the highlighted path
        known_cnt = sum(1 for cid in highlight_path if kg.is_known(cid))
        total = len(highlight_path)
        pct = (known_cnt / total) * 100 if total else 0.0
        names = [kg.concept_data(cid).get("name") for cid in highlight_path]
        st.markdown(
            f"**Path:** {' → '.join(names)}  \n"
            f"**Progress:** {known_cnt}/{total} ({pct:.0f}%)"
        )
        # Button to mark all nodes in the path as known
        if known_cnt < total:
            if st.button("Mark Entire Path Known"):
                for cid in highlight_path:
                    if not kg.is_known(cid):
                        kg.mark_known(cid)
                        GraphService.mark_concept_known(user.id, cid)
                st.success("Entire path marked as known.")
                _rerun()
    else:
        if ui_state["mode"] == "path" and ui_state["path_start"] and ui_state["path_end"]:
            st.info("No path found between the selected nodes.")

    # Node detail panel: show info about the currently selected node (in either mode)
    if selected_id is not None and kg.has_concept(selected_id):
        data = kg.concept_data(selected_id)
        st.subheader("Selected Node")
        st.write(f"**ID:** {selected_id}")
        st.write(f"**Name:** {data.get('name')}")
        st.write(f"**Known:** {data.get('known')}")
        if data.get("content"):
            with st.expander("Content"):
                st.markdown(data["content"])
