import streamlit as st

st.set_page_config(page_title="Quiz App", page_icon="🧠", layout="wide")

page = st.navigation([
    st.Page("app_pages/quiz.py", title="Quiz", icon=":material/quiz:", default=True),
    st.Page("app_pages/admin.py", title="Admin", icon=":material/admin_panel_settings:"),
])
page.run()