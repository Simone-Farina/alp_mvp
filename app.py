import streamlit as st
from dotenv import load_dotenv

from alp.core.ai_helper import detect_learning_style
from alp.core.parent_suggester import suggest_parent_via_ai
from alp.db.models import User
from alp.db.session import SessionLocal, session_scope

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
PAGE = st.sidebar.selectbox("Navigate", ["Dashboard", "Add Note", "Graph", "Learn"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_user():
    with session_scope() as db:
        return db.query(User).first()


def _compute_highlight_path(kg, path_start, path_end):
    if path_start is None or path_end is None:
        return None
    if path_start == path_end:
        return [path_start]
    return kg.shortest_path(path_start, path_end)


def _rerun():
    # Streamlit 1.30+ uses st.rerun; fall back if older
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
load_dotenv(".env")
st.title("Adaptive Learning Platform – MVP")

user = get_user()

# ---------------------------------------------------------------------------
# Onboarding
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
            style = detect_learning_style(answers)
            db = SessionLocal()
            db.add(User(name=name, learning_style=style))
            db.commit()
            db.close()
            st.success(
                f"Onboarding complete! Detected style: **{style}**. Reload to continue."
            )
            st.stop()

    st.stop()

# Sidebar info
st.sidebar.markdown(
    f"**User:** {user.name}  \nStyle: *{user.learning_style}*"
)

# Session-wide caches / UI state
if "kg_cache" not in st.session_state:
    st.session_state["kg_cache"] = {}

if "graph_ui" not in st.session_state:
    st.session_state["graph_ui"] = {
        "mode": "explore",  # 'explore' | 'path'
        "path_start": None,
        "path_end": None,
        "last_selected": None,  # track to avoid duplicate handling
    }

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
if PAGE == "Dashboard":
    st.header("Your Dashboard")
    st.write("Use **Add Note** to create concepts or **Graph** to explore your knowledge graph.")


# ---------------------------------------------------------------------------
# Add Note
# ---------------------------------------------------------------------------
elif PAGE == "Add Note":
    st.header("Add a new Note")

    title = st.text_input("Title / Topic")
    content = st.text_area("Markdown Content", height=220)
    parent = st.text_input(
        "Optional broader topic this fits under (leave blank for root)"
    )

    use_ai = st.checkbox("Let AI suggest parent topic")

    if use_ai and title and content:
        with st.spinner("Asking AI..."):
            suggestion = suggest_parent_via_ai(title, content)
            if suggestion:
                parent = suggestion
                st.success(f"AI suggests: **{parent}**")
            else:
                st.info("AI found no broader parent (root).")

    if st.button("Save Note"):
        if not title or not content:
            st.error("Title and content are required.")
        else:
            from alp.core.graph_ops import create_known_concept

            create_known_concept(user, title, content, parent or None)
            # Invalidate graph cache so new concept appears
            cache_key = f"kg_{user.id}"
            st.session_state["kg_cache"].pop(cache_key, None)
            st.success(f"Note '{title}' saved and added to your graph!")

# ---------------------------------------------------------------------------
# Learn Page
# ---------------------------------------------------------------------------
elif PAGE == "Learn":
    st.header("Generate Learning Path")

    topic = st.text_input("Target Topic", placeholder="e.g. Recursion")
    depth = st.slider("Depth (1=overview, 4=deep)", 1, 4, 2)
    max_nodes = st.number_input("Max nodes", 3, 30, 10, step=1)

    if st.button("Generate Path"):
        if not topic.strip():
            st.error("Please enter a topic.")
        else:
            from alp.graph.service import get_or_load_graph
            from alp.core.learning_plan import generate_learning_plan
            from alp.graph.inject import inject_learning_plan

            kg = get_or_load_graph(user.id, st.session_state["kg_cache"])
            # Sample known concepts (optional context compression)
            known_names = [
                data.get("name") for cid, data in kg.G.nodes(data=True)
                if data.get("known")
            ]
            # take a small sample to avoid huge prompts
            known_sample = known_names[:25]

            with st.spinner("Calling AI..."):
                plan = generate_learning_plan(topic, depth, user.learning_style, max_nodes, known_sample)

            if not plan:
                st.error("Failed to generate a learning plan (no API key or parse error).")
            else:
                added, reused, skipped = inject_learning_plan(
                    user.id, kg, plan, depth, max_nodes
                )
                # Invalidate any elements cache if you added one (optional)
                if "elements_cache" in st.session_state:
                    st.session_state["elements_cache"].clear()
                st.success(f"Integrated plan: {added} new, {reused} reused.")
                if skipped:
                    st.info(f"Skipped unknown prerequisites: {', '.join(skipped)}")

                st.markdown("### Injected Nodes (Filtered)")
                filtered = plan.filtered(depth, max_nodes)
                for node in filtered.nodes:
                    st.markdown(
                        f"- **{node.name}** (d{node['difficulty']}): "
                        f"{(node.get('summary') or '')[:200]}"
                    )
                st.markdown("Go to the **Graph** page to view them.")



# ---------------------------------------------------------------------------
# Graph Page
# ---------------------------------------------------------------------------
elif PAGE == "Graph":
    st.header("Knowledge Graph")

    from alp.graph.service import get_or_load_graph
    from streamlit_cytoscapejs import st_cytoscapejs

    ui = st.session_state["graph_ui"]

    # Load / cache KnowledgeGraph
    kg = get_or_load_graph(user.id, st.session_state["kg_cache"])

    # --- Top control row --------------------------------------------------
    col_reload, col_mode, col_reset, col_stats = st.columns([1, 1.3, 1.2, 3])
    with col_reload:
        if st.button("↻ Reload"):
            cache_key = f"kg_{user.id}"
            st.session_state["kg_cache"].pop(cache_key, None)
            ui["path_start"] = None
            ui["path_end"] = None
            _rerun()

    with col_mode:
        if ui["mode"] == "explore":
            if st.button("Enter Path Mode"):
                ui["mode"] = "path"
                ui["path_start"] = None
                ui["path_end"] = None
                _rerun()
        else:
            if st.button("Exit Path Mode"):
                ui["mode"] = "explore"
                ui["path_start"] = None
                ui["path_end"] = None
                _rerun()

    with col_reset:
        if st.button("Reset Path", disabled=(ui["path_start"] is None and ui["path_end"] is None)):
            ui["path_start"] = None
            ui["path_end"] = None
            _rerun()

    with col_stats:
        counts = kg.counts()
        st.caption(
            f"Nodes: {counts['nodes']} | Known: {counts['known']} | Edges: {counts['edges']} | Mode: {ui['mode']}"
        )

    # --- Compute highlight path BEFORE element build ----------------------
    highlight_path = _compute_highlight_path(kg, ui["path_start"], ui["path_end"])

    # --- Stylesheet -------------------------------------------------------
    stylesheet = [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "font-size": "10px",
                "text-valign": "center",
                "color": "#222",
                "background-color": "#bdc3c7",
                "width": "26px",
                "height": "26px",
                "border-width": "2px",
                "border-color": "#ecf0f1",
            },
        },
        {
            "selector": "node[known = 'True']",
            "style": {
                "background-color": "#27ae60",
                "border-color": "#145a32",
                "font-weight": "600",
                "color": "#fff",
            },
        },
        {
            "selector": "node[pathHighlight = 'true']",
            "style": {
                "border-color": "#f39c12",
                "border-width": "4px",
                "background-color": "#d35400",
                "color": "#fff",
            },
        },
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "target-arrow-color": "#7f8c8d",
                "line-color": "#7f8c8d",
                "width": 2,
                "arrow-scale": 1,
            },
        },
        {
            "selector": "edge[pathHighlight = 'true']",
            "style": {
                "line-color": "#f39c12",
                "target-arrow-color": "#f39c12",
                "width": 4,
            },
        },
    ]

    # --- Build elements with highlight ------------------------------------
    elements = kg.to_cytoscape_elements(highlight_path=highlight_path)

    # --- Render Graph -----------------------------------------------------
    selected_payload = st_cytoscapejs(
        elements=elements,
        stylesheet=stylesheet,
        width=800,
        height=600,
        key="cytograph",
    )

    # Extract selected node id
    selected_id = None
    if selected_payload and isinstance(selected_payload, dict):
        raw_sid = selected_payload.get("selected_node_id")
        if raw_sid is not None:
            try:
                selected_id = int(raw_sid)
            except ValueError:
                selected_id = None

    # --- Path Mode click handling -----------------------------------------
    if ui["mode"] == "path" and selected_id is not None:
        # Only react if selection changed
        if ui["last_selected"] != selected_id:
            if ui["path_start"] is None:
                ui["path_start"] = selected_id
                st.toast("Start node set.")
            elif ui["path_end"] is None and selected_id != ui["path_start"]:
                ui["path_end"] = selected_id
                st.toast("End node set.")
            elif selected_id == ui["path_start"]:
                # Toggle off / reset if user clicks the start again
                ui["path_start"] = None
                ui["path_end"] = None
                st.toast("Path cleared.")
            elif selected_id != ui["path_end"]:
                ui["path_end"] = selected_id
                st.toast("End node updated.")
            ui["last_selected"] = selected_id
            _rerun()

    # --- Path Summary / Actions -------------------------------------------
    if highlight_path:
        known_cnt = sum(1 for n in highlight_path if kg.is_known(n))
        total = len(highlight_path)
        pct = (known_cnt / total) * 100 if total else 0.0
        names = [kg.concept_data(n)["name"] for n in highlight_path]
        st.markdown(
            f"**Path:** {' → '.join(names)}  \n"
            f"**Progress:** {known_cnt}/{total} ({pct:.0f}%)"
        )
        # Bulk mark button
        if known_cnt < total:
            if st.button("Mark Entire Path Known"):
                from alp.graph.storage import mark_known_persist

                for n in highlight_path:
                    if not kg.is_known(n):
                        kg.mark_known(n)
                        mark_known_persist(user.id, n)
                st.success("Entire path marked as known.")
                _rerun()
    else:
        if ui["mode"] == "path" and ui["path_start"] and ui["path_end"]:
            st.info("No path found between selected nodes.")

    # --- Node Detail Panel ------------------------------------------------
    if selected_id is not None and kg.has_concept(selected_id):
        data = kg.concept_data(selected_id)
        st.subheader("Selected Node")
        st.write(f"**ID:** {selected_id}")
        st.write(f"**Name:** {data.get('name')}")
        st.write(f"**Known:** {data.get('known')}")
        if data.get("content"):
            with st.expander("Content"):
                st.markdown(data["content"])
        if not data.get("known"):
            if st.button("Mark as Known", key=f"mark_{selected_id}"):
                kg.mark_known(selected_id)
                from alp.graph.storage import mark_known_persist

                mark_known_persist(user.id, selected_id)
                st.success("Marked known.")
                _rerun()

    # --- Legend -----------------------------------------------------------
    with st.expander("Legend / Key", expanded=False):
        st.markdown(
            """
            - 🟢 **Known concept**
            - ⚪ **Unknown concept** (grey)
            - 🟧 **Path node** (orange border & fill)
            - 🟠 **Path edge** (orange line)
            - *Path Mode:* Click first node (start), second node (end); click start again to clear.
            """
        )
