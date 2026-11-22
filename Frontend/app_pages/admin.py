import streamlit as st
import requests
from config import API_URL

st.title("🛠️ Admin")

if "admin_password" not in st.session_state:
    st.session_state.admin_password = None


# ---------- Login ----------
if st.session_state.admin_password is None:
    with st.form("login_form"):
        password = st.text_input("Admin password", type="password")
        login = st.form_submit_button("Login", type="primary")

    if login:
        check = requests.get(f"{API_URL}/admin/questions", headers={"x-admin-password": password})
        if check.status_code == 200:
            st.session_state.admin_password = password
            st.rerun()
        else:
            st.error("❌ Wrong password")

    st.stop()


# ---------- Logged in ----------
HEADERS = {"x-admin-password": st.session_state.admin_password}

# Munnaadi action-oda message (rerun-ku apram kaata)
if "admin_message" in st.session_state:
    st.success(st.session_state.pop("admin_message"))


def logout():
    st.session_state.admin_password = None


def done(message):
    st.session_state.admin_message = message
    st.rerun()


questions = requests.get(f"{API_URL}/admin/questions", headers=HEADERS).json()

with st.container(horizontal=True, vertical_alignment="center"):
    st.caption(f"📝 Total questions: {len(questions)}")
    st.button("Logout", icon=":material/logout:", on_click=logout)

action = st.segmented_control(
    "What do you want to do?",
    ["📋 View", "➕ Add", "✏️ Edit", "🗑️ Delete"],
    default="📋 View",
)


def question_label(q):
    return f"#{q['id']}: {q['question']}"


# ---------- View ----------
if action == "📋 View":
    rows = []
    for q in questions:
        rows.append({
            "id": q["id"],
            "question": q["question"],
            "A": q["options"]["A"],
            "B": q["options"]["B"],
            "C": q["options"]["C"],
            "D": q["options"]["D"],
            "answer": q["answer"],
        })
    st.dataframe(rows, hide_index=True)

# ---------- Add ----------
elif action == "➕ Add":
    with st.form("add_form", clear_on_submit=True):
        question = st.text_area("Question")
        option_a = st.text_input("Option A")
        option_b = st.text_input("Option B")
        option_c = st.text_input("Option C")
        option_d = st.text_input("Option D")
        answer = st.segmented_control("Correct answer", ["A", "B", "C", "D"])
        add = st.form_submit_button("Add question", type="primary")

    if add:
        if "" in [question.strip(), option_a.strip(), option_b.strip(), option_c.strip(), option_d.strip()] or answer is None:
            st.warning("⚠️ Please fill all fields and choose the correct answer!")
        else:
            body = {
                "question": question,
                "option_a": option_a,
                "option_b": option_b,
                "option_c": option_c,
                "option_d": option_d,
                "answer": answer,
            }
            r = requests.post(f"{API_URL}/admin/questions", json=body, headers=HEADERS)
            if r.status_code == 200:
                done(f"✅ Question #{r.json()['id']} added!")
            else:
                st.error(r.json()["detail"])

# ---------- Edit ----------
elif action == "✏️ Edit":
    q = st.selectbox("Choose a question", questions, format_func=question_label)

    if q is not None:
        with st.form(f"edit_form_{q['id']}"):
            question = st.text_area("Question", value=q["question"])
            option_a = st.text_input("Option A", value=q["options"]["A"])
            option_b = st.text_input("Option B", value=q["options"]["B"])
            option_c = st.text_input("Option C", value=q["options"]["C"])
            option_d = st.text_input("Option D", value=q["options"]["D"])
            answer = st.segmented_control("Correct answer", ["A", "B", "C", "D"], default=q["answer"])
            save = st.form_submit_button("Save changes", type="primary")

        if save:
            if "" in [question.strip(), option_a.strip(), option_b.strip(), option_c.strip(), option_d.strip()] or answer is None:
                st.warning("⚠️ Please fill all fields and choose the correct answer!")
            else:
                body = {
                    "question": question,
                    "option_a": option_a,
                    "option_b": option_b,
                    "option_c": option_c,
                    "option_d": option_d,
                    "answer": answer,
                }
                r = requests.put(f"{API_URL}/admin/questions/{q['id']}", json=body, headers=HEADERS)
                if r.status_code == 200:
                    done(f"✅ Question #{q['id']} updated!")
                else:
                    st.error(r.json()["detail"])

# ---------- Delete ----------
elif action == "🗑️ Delete":
    q = st.selectbox("Choose a question", questions, format_func=question_label)

    if q is not None:
        st.write(f"**{q['question']}**")
        for key, value in q["options"].items():
            st.write(f"{key}) {value}")
        st.caption(f"Correct answer: {q['answer']}")

        sure = st.checkbox("Yes, I want to delete this question")
        if st.button("Delete question", type="primary", disabled=not sure):
            r = requests.delete(f"{API_URL}/admin/questions/{q['id']}", headers=HEADERS)
            if r.status_code == 200:
                done(f"🗑️ Question #{q['id']} deleted!")
            else:
                st.error(r.json()["detail"])