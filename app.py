import streamlit as st
from dotenv import load_dotenv
from alp.db.session import DB_PATH

load_dotenv()


st.set_page_config(page_title='ALP MVP', layout='centered')
st.title('Adaptive Learning Platform - MVP')
st.markdown(
    f"""
    **DB location:** `{DB_PATH}`
    This is just a skeleton.
    Use the sidebar to navigate when pages are added
    """
)

if st.checkbox("Run health check"):
    st.success("Streamlit is running and SQLite file exists.")