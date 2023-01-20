import functools
import sqlite3
import uuid

from flask import Flask, request

from yesterdays_hackernews import db

app = Flask(__name__)


@functools.cache()
def get_connection(db_file: Optional[str] = None):
    if db_file is None:
        db_file = os.environ["DB_FILE_LOC"]
    return sqlite3.connect(db_file, isolation_level=None)


def set_feedback(conn, colname, article_id, user_id, sentiment):
    with db.transaction(conn):
        conn.execute(
            "UPDATE feedback SET ?=? WHERE article_id=? AND user_id=?",
            (colname, sentiment, article_id, user_id),
        )


@app.route("/feedback/bad_inlining")
def bad_inlining_route():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    if user_id is None:
        return "No user_id provided", 400
    if article_id is None:
        return "No article_id provided", 400
    conn = get_connection()
    set_feedback(
        conn=conn,
        colname="format_quality",
        article_id=article_id,
        user_id=user_id,
        sentiment=-1,
    )


@app.route("/feedback/good_inlining")
def good_inlining_route():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    if user_id is None:
        return "No user_id provided", 400
    if article_id is None:
        return "No article_id provided", 400
    conn = get_connection()
    set_feedback(
        conn=conn,
        colname="format_quality",
        article_id=article_id,
        user_id=user_id,
        sentiment=1,
    )


@app.route("/feedback/dont_inline")
def dont_inline_route():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    if user_id is None:
        return "No user_id provided", 400
    if article_id is None:
        return "No article_id provided", 400
    conn = get_connection()
    set_feedback(
        conn=conn,
        colname="should_format",
        article_id=article_id,
        user_id=user_id,
        sentiment=-1,
    )


@app.route("/feedback/do_inline")
def do_inline_route():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    if user_id is None:
        return "No user_id provided", 400
    if article_id is None:
        return "No article_id provided", 400
    conn = get_connection()
    set_feedback(
        conn=conn,
        colname="should_format",
        article_id=article_id,
        user_id=user_id,
        sentiment=1,
    )


@app.route("/feedback/not_interesting")
def not_interesting_route():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    if user_id is None:
        return "No user_id provided", 400
    if article_id is None:
        return "No article_id provided", 400
    conn = get_connection()
    set_feedback(
        colname="sentiment", article_id=article_id, user_id=user_id, sentiment=-1
    )


@app.route("/feedback/interesting")
def interesting_route():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    if user_id is None:
        return "No user_id provided", 400
    if article_id is None:
        return "No article_id provided", 400
    conn = get_connection()
    set_feedback(
        colname="sentiment", article_id=article_id, user_id=user_id, sentiment=1
    )


def unsubscribe(conn, user_id):
    with db.transaction(conn):
        conn.execute(
            "UPDATE users SET num_articles_per_day=? WHERE user_id=?", (0, user_id)
        )


@app.route("/unsubscribe")
def unsubscribe_route():
    user_id = request.args.get("user_id")
    if user_id is None:
        return "No user_id", 400
    conn = get_connection()
    unsubscribe(conn=conn, user_id=user_id)


def confirm(conn, email):
    with db.transaction(conn):
        conn.execute(
            """UPDATE users SET confirmed=? WHERE email=?""",
            (1, email),
        )


@app.route("/confirm")
def confirm_route():
    user_id = request.args.get("email")
    if user_id is None:
        return "No user_id", 400
    conn = get_connection()
    confirm(email)


def subscribe(conn, email, user_id, num_articles_per_day):
    with db.transaction(conn):
        conn.execute(
            """INSERT INTO users(email,user_id,num_articles_per_day, confirmed) VALUES(?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET num_articles_per_day=?;""",
            (email, user_id, num_articles_per_day, 0, num_articles_per_day),
        )


@app.route("/subscribe")
def subscribe_route():
    email = request.args.get("email")
    user_id = uuid.uuid4()
    num_emails_per_day = request.args.get("num_emails_per_day")
    if num_articles_per_day:
        try:
            num_articles_per_day = int(num_articles_per_day)
        except ValueError:
            num_articles_per_day = None

    if num_articles_per_day is None:
        num_articles_per_day = 10

    if user_id is None:
        return "No user_id", 400

    if email is None:
        return "No email", 400
    conn = get_connection()
    subscribe(
        conn=conn,
        email=email,
        user_id=user_id,
        num_articles_per_day=num_articles_per_day,
    )


if __name__ == "__main__":
    app.run()
