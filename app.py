import streamlit as st
from dotenv import load_dotenv

from alp.core.ai_helper import detect_learning_style
from alp.db.models import User
from alp.db.session import SessionLocal

PAGE = st.sidebar.selectbox("Navigate", ["Dashboard", "Add Note"])


def get_user():
    db = SessionLocal()
    user = db.query(User).first()
    if user:
        db.close()
        return user
    return None


load_dotenv()

# st.set_page_config(page_title='ALP MVP', layout='centered')
st.title("Adaptive Learning Platform – MVP")

user = get_user()

if user is None:
    st.subheader("Onboarding – Discover your learning style")

    name = st.text_input("Your name", "")
    q1 = st.selectbox(
        "When learning something new, what do you prefer?",
        ["Watching diagrams/videos", "Listening to explanations", "Hands‑on practice", "Reading detailed text"]
    )
    q2 = st.selectbox(
        "Which sounds more appealing?",
        ["A colourful mind‑map", "An engaging podcast", "Building a prototype", "Reading a research paper"]
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
            st.success(f"Onboarding complete! Detected style: **{style}**. Reload to continue.")
            st.stop()

else:
    st.sidebar.markdown(f"**User:** {user.name}  \nStyle: *{user.learning_style}*")

    if PAGE == "Dashboard":
        st.header("Your Dashboard")
        st.write("Graph view & learning paths coming next.")
    elif PAGE == "Add Note":
        st.header("Add a new Note")

        title = st.text_input("Title / Topic")
        content = st.text_area("Markdown Content", height=200)
        # IDEA: this text input should autocomplete from available graph nodes
        parent = st.text_input(
            "Optional broader topic this fits under (leave blank for root)"
        )
        if st.button("Save Note"):
            if not title or not content:
                st.error("Title and content are required.")
            else:
                from alp.core.graph_ops import create_known_concept

                create_known_concept(user, title, content, parent or None)
                st.success(f"Note '{title}' saved and added to your graph!")
