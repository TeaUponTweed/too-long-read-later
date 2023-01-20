import functools
import sqlite3
import uuid
from typing import Optional

from flask import Flask, request

from yesterdays_hackernews import utils

api = Flask(__name__)


@api.route("/feedback/<col_name>")
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
            conn = utils.get_connection()
            utils.set_feedback(
                conn=conn,
                col_name=col_name,
                article_id=article_id,
                user_id=user_id,
                sentiment=sentiment,
            )
            return "Success", 200


@api.route("/unsubscribe")
def unsubscribe_route():
    user_id = request.args.get("user_id")
    if user_id is None:
        return "No user_id", 400
    conn = utils.get_connection()
    utils.unsubscribe(conn=conn, user_id=user_id)
    return "Success", 200


@api.route("/confirm")
def confirm_route():
    user_id = request.args.get("email")
    if user_id is None:
        return "No user_id", 400
    conn = utils.get_connection()
    utils.confirm(conn=conn, email=email)
    return "Success", 200


@api.route("/subscribe")
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

    conn = utils.get_connection()
    utils.subscribe(
        conn=conn,
        email=email,
        user_id=user_id,
        num_articles_per_day=num_articles_per_day,
    )
    return "Success", 200


if __name__ == "__main__":
    api.run()
