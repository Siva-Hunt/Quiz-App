import streamlit as st
import requests
from config import API_URL

st.title("🧠 Quiz App")

response = requests.get(f"{API_URL}/questions")
questions = response.json()
total = len(questions)

if total == 0:
    st.info("No questions yet. Ask the admin to add some! 🛠️")
    st.stop()

# ---------- Memory setup ----------
if "player_name" not in st.session_state:
    st.session_state.player_name = None
if "current" not in st.session_state:
    st.session_state.current = 0
if "result" not in st.session_state:
    st.session_state.result = None

# Admin question delete pannirundha, index list-ku veliya pogaama
if st.session_state.current >= total:
    st.session_state.current = total - 1


# ---------- Button functions ----------
def go_next():
    st.session_state.current += 1


def go_previous():
    st.session_state.current -= 1


def restart_quiz():
    for question in questions:
        st.session_state.pop(f"q{question['id']}", None)
    st.session_state.current = 0
    st.session_state.result = None


def new_player():
    restart_quiz()
    st.session_state.player_name = None


# ---------- Leaderboard ----------
def show_leaderboard():
    st.subheader("🏆 Leaderboard")
    board = requests.get(f"{API_URL}/leaderboard").json()

    if len(board) == 0:
        st.caption("No scores yet. Be the first! 🚀")
    else:
        st.dataframe(
            board,
            column_order=["rank", "name", "score", "total", "percentage"],
            column_config={
                "rank": st.column_config.NumberColumn("🏅 Rank"),
                "name": "👤 Name",
                "score": "✅ Score",
                "total": "📝 Total",
                "percentage": st.column_config.NumberColumn("📊 Percentage", format="%.1f%%"),
            },
            hide_index=True,
        )


# ---------- Screen 1: Name ----------
if st.session_state.player_name is None:
    name = st.text_input("Enter your name to start:", max_chars=30)

    if st.button("Start Quiz ▶️", type="primary"):
        if name.strip() == "":
            st.warning("⚠️ Please enter your name!")
        else:
            st.session_state.player_name = name.strip()
            st.rerun()

    show_leaderboard()

# ---------- Screen 2: Quiz ----------
elif st.session_state.result is None:
    st.caption(f"👤 Player: {st.session_state.player_name}")

    index = st.session_state.current
    question = questions[index]

    st.progress((index + 1) / total, text=f"Question {index + 1} of {total}")
    st.subheader(f"Q{index + 1}. {question['question']}")

    options = question["options"]
    st.radio(
        "Choose your answer:",
        list(options.keys()),
        format_func=lambda key: f"{key}) {options[key]}",
        index=None,
        key=f"q{question['id']}",
        persist_state="page",
    )

    submitted = False
    with st.container(horizontal=True):
        st.button("⬅️ Previous", on_click=go_previous, disabled=index == 0)
        if index < total - 1:
            st.button("Next ➡️", on_click=go_next)
        else:
            submitted = st.button("Submit Quiz", type="primary")

    if submitted:
        answers = []
        unanswered = []
        for number, q in enumerate(questions, start=1):
            selected = st.session_state.get(f"q{q['id']}")
            if selected is None:
                unanswered.append(number)
            else:
                answers.append({"question_id": q["id"], "selected_answer": selected})

        if unanswered:
            st.warning(f"⚠️ Please answer these questions: {unanswered}")
        else:
            result = requests.post(
                f"{API_URL}/submit-quiz",
                json={"name": st.session_state.player_name, "answers": answers},
            )
            st.session_state.result = result.json()
            st.rerun()

# ---------- Screen 3: Result ----------
else:
    data = st.session_state.result

    st.success(f"🎯 {st.session_state.player_name}, your score: {data['score']} / {data['total']}")
    st.info(f"📊 Percentage: {data['percentage']}%")

    show_leaderboard()

    st.subheader("Answer review")
    for number, r in enumerate(data["results"], start=1):
        if r["is_correct"]:
            st.success(f"✅ Q{number}: Correct! (You chose {r['selected_answer']})")
        else:
            st.error(
                f"❌ Q{number}: Wrong. You chose {r['selected_answer']}. "
                f"Correct answer: {r['correct_answer']}) {r['correct_text']}"
            )

    with st.container(horizontal=True):
        st.button("🔄 Play Again", on_click=restart_quiz)
        st.button("👤 New Player", on_click=new_player)