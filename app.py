from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from config import DB_CONFIG

app = Flask(__name__)

app.secret_key = "quizmaster-secret-key"

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

@app.route("/")
def home():
    return redirect(url_for("register"))

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
        """

        cursor.execute(
            query,
            (username, email, hashed_password)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT * FROM users
            WHERE email = %s
        """

        cursor.execute(query, (email,))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )

@app.route("/admin")
def admin():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    return render_template("admin.html")

@app.route("/admin/questions")
def admin_questions():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            questions.question_id,
            questions.question,
            questions.option_a,
            questions.option_b,
            questions.option_c,
            questions.option_d,
            questions.correct_answer,
            categories.category_name
        FROM questions
        JOIN categories
            ON questions.category_id = categories.category_id
        ORDER BY questions.question_id DESC
    """

    cursor.execute(query)
    questions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_questions.html",
        questions=questions
    )

@app.route("/admin/questions/add", methods=["GET", "POST"])
def add_question():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        category_id = request.form["category_id"]
        question = request.form["question"]
        option_a = request.form["option_a"]
        option_b = request.form["option_b"]
        option_c = request.form["option_c"]
        option_d = request.form["option_d"]
        correct_answer = request.form["correct_answer"]

        query = """
            INSERT INTO questions
            (category_id, question, option_a, option_b, option_c, option_d, correct_answer)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                category_id,
                question,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("admin_questions"))

    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "add_question.html",
        categories=categories
    )

@app.route("/admin/questions/edit/<int:question_id>", methods=["GET", "POST"])
def edit_question(question_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        category_id = request.form["category_id"]
        question = request.form["question"]
        option_a = request.form["option_a"]
        option_b = request.form["option_b"]
        option_c = request.form["option_c"]
        option_d = request.form["option_d"]
        correct_answer = request.form["correct_answer"]

        query = """
            UPDATE questions
            SET category_id = %s,
                question = %s,
                option_a = %s,
                option_b = %s,
                option_c = %s,
                option_d = %s,
                correct_answer = %s
            WHERE question_id = %s
        """

        cursor.execute(
            query,
            (
                category_id,
                question,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer,
                question_id
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("admin_questions"))

    cursor.execute(
        "SELECT * FROM questions WHERE question_id = %s",
        (question_id,)
    )

    question_data = cursor.fetchone()

    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "edit_question.html",
        question=question_data,
        categories=categories
    )   
@app.route("/admin/questions/delete/<int:question_id>", methods=["POST"])
def delete_question(question_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "DELETE FROM questions WHERE question_id = %s"

    cursor.execute(query, (question_id,))
    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("admin_questions"))

@app.route("/history")
def history():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT 
            quiz_attempts.attempt_id,
            categories.category_name,
            quiz_attempts.score,
            quiz_attempts.total_questions,
            quiz_attempts.date_taken
        FROM quiz_attempts
        JOIN categories
            ON quiz_attempts.category_id = categories.category_id
        WHERE quiz_attempts.user_id = %s
        ORDER BY quiz_attempts.date_taken DESC
    """

    cursor.execute(query, (session["user_id"],))
    attempts = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "history.html",
        attempts=attempts
    )

@app.route("/leaderboard")
def leaderboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            users.username,
            categories.category_name,
            quiz_attempts.score,
            quiz_attempts.total_questions
        FROM quiz_attempts
        JOIN users
            ON quiz_attempts.user_id = users.user_id
        JOIN categories
            ON quiz_attempts.category_id = categories.category_id
        ORDER BY quiz_attempts.score DESC
    """

    cursor.execute(query)
    leaderboard_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "leaderboard.html",
        leaderboard=leaderboard_data
    )
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

@app.route("/categories")
def categories():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "categories.html",
        categories=categories
    )
@app.route("/quiz/<int:category_id>", methods=["GET", "POST"])
def quiz(category_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # GET = random questions
    if request.method == "GET":

        query = """
            SELECT * FROM questions
            WHERE category_id = %s
            ORDER BY RAND()
            LIMIT 10
        """

        cursor.execute(query, (category_id,))
        questions = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template(
            "quiz.html",
            questions=questions
        )

# POST = kunin ang exact questions na sinagutan
    question_ids = [
        int(qid)
        for qid in request.form["quiz_question_ids"].split(",")
    ]

    if not question_ids:
        cursor.close()
        connection.close()
        return redirect(url_for("categories"))

    placeholders = ",".join(["%s"] * len(question_ids))

    query = f"""
        SELECT * FROM questions
        WHERE category_id = %s
        AND question_id IN ({placeholders})
    """

    cursor.execute(
        query,
        [category_id] + question_ids
    )

    questions = cursor.fetchall()
    # Check answers
    score = 0

    for question in questions:

        user_answer = request.form.get(
            f"question_{question['question_id']}"
        )

        if user_answer == question["correct_answer"]:
            score += 1

    total_questions = len(questions)

    # Save quiz attempt
    insert_query = """
        INSERT INTO quiz_attempts
        (user_id, category_id, score, total_questions)
        VALUES (%s, %s, %s, %s)
    """

    cursor.execute(
        insert_query,
        (
            session["user_id"],
            category_id,
            score,
            total_questions
        )
    )

    connection.commit()

    attempt_id = cursor.lastrowid

    # Save individual answers
    for question in questions:

        user_answer = request.form.get(
            f"question_{question['question_id']}"
        )

        is_correct = user_answer == question["correct_answer"]

        answer_query = """
            INSERT INTO quiz_answers
            (attempt_id, question_id, user_answer, is_correct)
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            answer_query,
            (
                attempt_id,
                question["question_id"],
                user_answer,
                is_correct
            )
        )

    connection.commit()

    cursor.close()
    connection.close()

    return render_template(
        "result.html",
        score=score,
        total=total_questions
    )


if __name__ == "__main__":
    app.run(debug=True)