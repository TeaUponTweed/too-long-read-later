import functools
import sqlite3
import urllib
import uuid
from typing import Optional

from flask import Flask, request, send_file, send_from_directory

from yesterdays_hackernews import utils
from yesterdays_hackernews.send import send_mesage

api = Flask(__name__)


@api.route("/feedback/<col_name>")
def feedback_route(col_name: str):
    user_uuid = request.args.get("user_uuid")
    article_id = request.args.get("article_id")
    sentiment = request.args.get("sentiment")
    if user_uuid is None:
        return "No user_uuid provided", 400
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
            try:
                user_info = utils.get_user_info(conn=conn, user_uuid=user_uuid)
                utils.set_feedback(
                    conn=conn,
                    col_name=col_name,
                    article_id=article_id,
                    user_id=user_info.row_id,
                    sentiment=sentiment,
                )
            except ValueError:
                return "Bad feedback column", 400
            else:
                # TODO allow a person to undo the feedback
                return "Success", 200


@api.route("/unsubscribe")
def unsubscribe_route():
    user_uuid = request.args.get("user_uuid")
    if user_uuid is None:
        return "No user_uuid", 400
    conn = utils.get_connection()
    utils.unsubscribe(conn=conn, user_uuid=user_uuid)
    return "Success", 200


@api.route("/confirm")
def confirm_route():
    user_uuid = request.args.get("user_uuid")
    if user_uuid is None:
        return "No user_uuid", 400
    conn = utils.get_connection()
    user_info = utils.get_user_info(conn=conn, user_uuid=user_uuid)
    if user_info is not None:
        utils.confirm(conn=conn, email=user_info.email)
        return "Success", 200
    else:
        return "Unrecognized user_uuid", 400


@api.route("/subscribe")
def subscribe_route():
    email = request.args.get("email")
    num_articles_per_day = request.args.get("num_articles_per_day")
    if num_articles_per_day:
        try:
            num_articles_per_day = int(num_articles_per_day)
        except ValueError:
            num_articles_per_day = None

    if num_articles_per_day is None:
        num_articles_per_day = 10

    if email is None:
        return "No email", 400

    email = email.lower()

    conn = utils.get_connection()
    user_info = utils.get_user_info(conn=conn, email=email)
    if user_info is None:
        user_uuid = str(uuid.uuid4())
    else:
        user_uuid = user_info.user_uuid
    utils.subscribe(
        conn=conn,
        email=email,
        user_uuid=user_uuid,
        num_articles_per_day=num_articles_per_day,
    )
    if user_info is None or not user_info.confirmed:
        confirm_url = "news.derivativeworks.co/confirm?" + urllib.parse.urlencode(
            {
                "user_uuid": str(user_uuid),
            }
        )
        msg = f"""
        <a href="{confirm_url}"> Please follow this URL to confirm email.</a>
        <br>
        <p>
            You can update news prefereces by visiting news.derivativeworks.co
        </p>
        """
        send_mesage(
            to=email,
            subject="Please Confirm Email For news.derivativeworks.co",
            msg=msg,
        )
        return "Success. Please confirm your email.", 200
    else:
        return "Success. Prefereces updated", 200


@api.route("/")
def home():
    return send_file("static/index.html")


@api.route("/static/<path:path>")
def send_static(path):
    return send_from_directory("static", path)


if __name__ == "__main__":
    api.run(host="0.0.0.0", port=5001)
