import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# .env file-la irundhu secrets load pannum (local computer-ku mattum)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not DATABASE_URL or not ADMIN_PASSWORD:
    raise RuntimeError("DATABASE_URL and ADMIN_PASSWORD must be set (check Backend/.env)")

app = FastAPI()


# ---------- Models ----------
class AnswerRequest(BaseModel):
    question_id: int
    selected_answer: str


class QuizSubmission(BaseModel):
    name: str = "Anonymous"
    answers: list[AnswerRequest]


class QuestionInput(BaseModel):
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    answer: str


# ---------- Starting questions (first time mattum DB-la podum) ----------
seed_questions = [
    ("What is Python?", "Programming Language", "Database", "Browser", "Operating System", "A"),
    ("What is SQL?", "Programming Language", "Database Language", "Web Browser", "Operating System", "B"),
    ("Which library is used for data analysis?", "Pandas", "FastAPI", "Streamlit", "Flask", "A"),
    ("Which keyword is used to define a function in Python?", "def", "func", "function", "define", "A"),
    ("Which data type stores key-value pairs?", "List", "Tuple", "Dictionary", "Set", "C"),
    ("What is the output of len([1, 2, 3])?", "2", "3", "4", "Error", "B"),
    ("Which symbol is used for comments in Python?", "//", "/* */", "#", "--", "C"),
    ("Which method adds an item to the end of a list?", "add()", "insert()", "push()", "append()", "D"),
    ("Which SQL command is used to retrieve data?", "GET", "SELECT", "FETCH", "READ", "B"),
    ("Which SQL clause is used to filter rows?", "ORDER BY", "GROUP BY", "WHERE", "LIMIT", "C"),
    ("Which SQL command adds new rows to a table?", "INSERT INTO", "ADD ROW", "UPDATE", "CREATE", "A"),
    ("Which SQL function counts the number of rows?", "SUM()", "TOTAL()", "NUMBER()", "COUNT()", "D"),
    ("Which Pandas function reads a CSV file?", "pd.read_csv()", "pd.open_csv()", "pd.load_csv()", "pd.csv()", "A"),
    ("Which Pandas method shows the first 5 rows?", "top()", "first()", "head()", "start()", "C"),
    ("What is a 2D table in Pandas called?", "Series", "DataFrame", "Array", "Matrix", "B"),
    ("Which HTTP method is used to send data to an API?", "GET", "POST", "OPEN", "SEND", "B"),
    ("Which command runs a FastAPI app?", "python run main", "fastapi start", "uvicorn main:app --reload", "streamlit run main.py", "C"),
    ("Which URL shows the FastAPI automatic docs?", "/help", "/api", "/swagger", "/docs", "D"),
    ("Which command runs a Streamlit app?", "streamlit run app.py", "python start app.py", "uvicorn app:app", "run streamlit", "A"),
    ("Which Streamlit widget lets the user pick one option from a list?", "st.button", "st.title", "st.write", "st.radio", "D"),
    ("What does CSV stand for?", "Comma Separated Values", "Computer Style View", "Central Sheet Value", "Code Saved Variable", "A"),
]


# ---------- Database helpers ----------
def get_db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                percentage REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                answer TEXT NOT NULL
            )
        """)

        count = conn.execute("SELECT COUNT(*) AS total FROM questions").fetchone()["total"]
        if count == 0:
            conn.cursor().executemany(
                "INSERT INTO questions (question, option_a, option_b, option_c, option_d, answer) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                seed_questions
            )


def load_questions():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM questions ORDER BY id").fetchall()

    questions = []
    for row in rows:
        questions.append({
            "id": row["id"],
            "question": row["question"],
            "options": {
                "A": row["option_a"],
                "B": row["option_b"],
                "C": row["option_c"],
                "D": row["option_d"]
            },
            "answer": row["answer"]
        })
    return questions


def check_admin(password):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong admin password")


def clean_question(data: QuestionInput):
    answer = data.answer.strip().upper()
    if answer not in ["A", "B", "C", "D"]:
        raise HTTPException(status_code=400, detail="Answer must be A, B, C or D")
    return (
        data.question.strip(),
        data.option_a.strip(),
        data.option_b.strip(),
        data.option_c.strip(),
        data.option_d.strip(),
        answer
    )


init_db()


# ---------- Quiz APIs ----------
@app.get("/")
def home():
    return {"message": "Welcome to Quiz App"}


@app.get("/questions")
def get_questions():
    quiz_questions = []

    for question in load_questions():
        quiz_questions.append({
            "id": question["id"],
            "question": question["question"],
            "options": question["options"]
        })

    return quiz_questions


@app.post("/submit-answer")
def submit_answer(data: AnswerRequest):

    for question in load_questions():
        if question["id"] == data.question_id:

            if question["answer"] == data.selected_answer.strip().upper():
                return {"result": "Correct Answer!"}
            else:
                return {"result": "Wrong Answer!"}

    return {"error": "Question not found"}


@app.post("/submit-quiz")
def submit_quiz(data: QuizSubmission):
    questions = load_questions()
    score = 0
    results = []

    for user_answer in data.answers:
        for question in questions:
            if question["id"] == user_answer.question_id:
                selected = user_answer.selected_answer.strip().upper()
                correct = question["answer"]
                is_correct = selected == correct

                if is_correct:
                    score = score + 1

                results.append({
                    "question_id": question["id"],
                    "selected_answer": selected,
                    "correct_answer": correct,
                    "correct_text": question["options"][correct],
                    "is_correct": is_correct
                })

    total = len(questions)
    percentage = round((score / total) * 100, 2)

    player_name = data.name.strip() or "Anonymous"

    with get_db() as conn:
        conn.execute(
            "INSERT INTO scores (name, score, total, percentage) VALUES (%s, %s, %s, %s)",
            (player_name, score, total, percentage)
        )

    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": results
    }


@app.get("/leaderboard")
def get_leaderboard():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT name, score, total, percentage, created_at
            FROM scores
            ORDER BY score DESC, created_at ASC
            LIMIT 10
        """).fetchall()

    leaderboard = []
    for rank, row in enumerate(rows, start=1):
        leaderboard.append({
            "rank": rank,
            "name": row["name"],
            "score": row["score"],
            "total": row["total"],
            "percentage": row["percentage"],
            "played_at": row["created_at"]
        })

    return leaderboard


# ---------- Admin APIs (password venum) ----------
@app.get("/admin/questions")
def admin_get_questions(x_admin_password: str = Header()):
    check_admin(x_admin_password)
    return load_questions()


@app.post("/admin/questions")
def admin_add_question(data: QuestionInput, x_admin_password: str = Header()):
    check_admin(x_admin_password)
    values = clean_question(data)

    with get_db() as conn:
        new_id = conn.execute(
            "INSERT INTO questions (question, option_a, option_b, option_c, option_d, answer) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            values
        ).fetchone()["id"]

    return {"message": "Question added", "id": new_id}


@app.put("/admin/questions/{question_id}")
def admin_update_question(question_id: int, data: QuestionInput, x_admin_password: str = Header()):
    check_admin(x_admin_password)
    values = clean_question(data)

    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE questions SET question = %s, option_a = %s, option_b = %s, option_c = %s, "
            "option_d = %s, answer = %s WHERE id = %s",
            values + (question_id,)
        )

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"message": "Question updated", "id": question_id}


@app.delete("/admin/questions/{question_id}")
def admin_delete_question(question_id: int, x_admin_password: str = Header()):
    check_admin(x_admin_password)

    with get_db() as conn:
        cursor = conn.execute("DELETE FROM questions WHERE id = %s", (question_id,))

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"message": "Question deleted", "id": question_id}