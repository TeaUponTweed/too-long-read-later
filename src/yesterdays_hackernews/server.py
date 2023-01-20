import sqlite3
import uuid

from flask import Flask, request

from yesterdays_hackernews import db

app = Flask(__name__)

_DB_FILE = os.environ["DB_FILE_LOC"] if "DB_FILE_LOC" in os.environ else "data/news.db"
_CONN = sqlite3.connect(_DB_FILE, isolation_level=None)


@app.route("/feedback/bad_inlining")
def bad_inlining():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    with db.transaction(conn):
        conn.execute(
            "UPDATE feedback SET format_quality=? WHERE article_id=? AND user_id=?",
            (-1, article_id, user_id),
        )


@app.route("/feedback/good_inlining")
def good_inlining():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    with db.transaction(conn):
        conn.execute(
            "UPDATE feedback SET format_quality=? WHERE article_id=? AND user_id=?",
            (1, article_id, user_id),
        )


@app.route("/feedback/dont_inline")
def dont_inline():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    with db.transaction(conn):
        conn.execute(
            "UPDATE feedback SET should_format=? WHERE article_id=? AND user_id=?",
            (-1, article_id, user_id),
        )


@app.route("/feedback/do_inline")
def do_inline():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    with db.transaction(conn):
        conn.execute(
            "UPDATE feedback SET should_format=? WHERE article_id=? AND user_id=?",
            (1, article_id, user_id),
        )


@app.route("/feedback/not_interesting")
def not_interesting():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    with db.transaction(conn):
        conn.execute(
            "UPDATE feedback SET sentiment=? WHERE article_id=? AND user_id=?",
            (-1, article_id, user_id),
        )


@app.route("/feedback/interesting")
def interesting():
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    with db.transaction(conn):
        conn.execute(
            "UPDATE feedback SET sentiment=? WHERE article_id=? AND user_id=?",
            (1, article_id, user_id),
        )


@app.route("/unsubscribe")
def unsubscribe():
    user_id = request.args.get("user_id")
    conn.execute(
        "UPDATE users SET num_articles_per_day=? WHERE user_id=?", (0, user_id)
    )


@app.route("/subscribe")
def subscribe():
    user_id = request.args.get("user_id")
    num_emails_per_day = request.args.get("num_emails_per_day")
    if num_articles_per_day:
        num_articles_per_day = int(num_articles_per_day)
    else:
        num_articles_per_day = 10
    conn.execute(
        """
        INSERT INTO users(user_id,num_articles_per_day) VALUES(?,"")
        ON CONFLICT(user_id) DO UPDATE SET num_articles_per_day=?;
    """,
        (user_id, num_articles_per_day),
    )


if __name__ == "__main__":
    app.run()
