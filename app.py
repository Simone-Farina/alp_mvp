import streamlit as st
from dotenv import load_dotenv

from alp.core.ai_helper import detect_learning_style
from alp.db.models import User
from alp.db.session import SessionLocal


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
    st.success(f"Welcome back, **{user.name}**. Your learning style: **{user.learning_style}**")
    st.write("🎯 Next: add notes or request a learning path. (Coming in next milestones)")
