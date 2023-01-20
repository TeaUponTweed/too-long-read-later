import functools
import sqlite3
import uuid
from typing import Optional

from flask import Flask, request

from yesterdays_hackernews import db

app = Flask(__name__)


@functools.cache()
def get_connection(db_file: Optional[str] = None) -> sqlite3.Connection:
    if db_file is None:
        db_file = os.environ["DB_FILE_LOC"]
    return sqlite3.connect(db_file, isolation_level=None)


def set_feedback(
    conn: sqlite3.Connection,
    colname: str,
    article_id: int,
    user_id: str,
    sentiment: int,
):
    with db.transaction(conn):
        conn.execute(
            "UPDATE feedback SET ?=? WHERE article_id=? AND user_id=?",
            (colname, sentiment, article_id, user_id),
        )


def confirm(conn: sqlite3.Connection, email: str):
    with db.transaction(conn):
        conn.execute(
            """UPDATE users SET confirmed=? WHERE email=?""",
            (1, email),
        )


def unsubscribe(conn: sqlite3.Connection, user_id: str):
    with db.transaction(conn):
        conn.execute(
            "UPDATE users SET num_articles_per_day=? WHERE user_id=?", (0, user_id)
        )


def subscribe(
    conn: sqlite3.Connection, email: str, user_id: str, num_articles_per_day: int
):
    with db.transaction(conn):
        conn.execute(
            """INSERT INTO users(email,user_id,num_articles_per_day, confirmed) VALUES(?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET num_articles_per_day=?;""",
            (email, user_id, num_articles_per_day, 0, num_articles_per_day),
        )


def get_email(conn: sqlite3.Connection, user_id: str) -> Optional[str]:
    with db.transaction(conn):
        ret = conn.execute(
            "SELCT email from users where user_id = ?", user_id
        ).fetchone()
    if len(ret):
        return ret[0]
    else:
        return None


def get_user_id(conn: sqlite3.Connection, email: str) -> Optional[str]:
    with db.transaction(conn):
        ret = conn.execute("SELCT user_id from users where email = ?", email).fetchone()
    if len(ret):
        return ret[0]
    else:
        return None


@app.route("/feedback/<col_name>")
def feedback_route(col_name: str):
    user_id = request.args.get("user_id")
    article_id = request.args.get("article_id")
    sentiment = request.args.get("sentiment")
    if user_id is None:
        return "No user_id provided", 400
    if article_id is None:
        return "No article_id provided", 400
    if sentiment is None:
        return "No sentiment provided", 400
    try:
        sentiment = int(sentiment)
    except ValueError:
        return "Bad value for sentiment", 400
    else:
        try:
            article_id = int(article_id)
        except ValueError:
            return "Bad value for article_id", 400
        else:
            conn = get_connection()
            set_feedback(
                conn=conn,
                col_name=col_name,
                article_id=article_id,
                user_id=user_id,
                sentiment=sentiment,
            )
            return "Success", 200


@app.route("/unsubscribe")
def unsubscribe_route():
    user_id = request.args.get("user_id")
    if user_id is None:
        return "No user_id", 400
    conn = get_connection()
    unsubscribe(conn=conn, user_id=user_id)
    return "Success", 200


@app.route("/confirm")
def confirm_route():
    user_id = request.args.get("email")
    if user_id is None:
        return "No user_id", 400
    conn = get_connection()
    confirm(conn=conn, email=email)
    return "Success", 200


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
    return "Success", 200


if __name__ == "__main__":
    app.run()
