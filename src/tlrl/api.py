import functools
import sqlite3
import urllib
import uuid
from typing import Optional

import pandas as pd
from flask import Flask, jsonify, redirect, request, send_file, send_from_directory

from tlrl import db, utils
from tlrl.scraper import ingest_impl
from tlrl.send import send_mesage
from tlrl.sender import _prepare_email

api = Flask(__name__)


@api.route("/tlrl", methods=["POST"])
def tlrl():
    data = request.get_json()
    if "url" in data:
        url = data["url"]
    else:
        return jsonify(error="url is required"), 400

    email = data["email"]
    if "email" in data:
        email = data["email"]
    else:
        return jsonify(error="email is required"), 400

    # url = request.args.get("url")
    # email = request.args.get("email")
    # if email is None:
    #     return "No email provided", 400
    # if url is None:
    #     return "No url provided", 400

    if len(email) == 0:
        return jsonify(error="Email is null. Are you signed in?"), 400

    url = urllib.parse.unquote(url)

    conn = utils.get_connection()
    user_info = utils.get_user_info(conn=conn, email=email)
    if user_info is None:
        return "Unknown email", 400
    # get content
    df = pd.DataFrame.from_dict([ingest_impl(link=url, date="TLRL-ADHOC")])
    # add to database
    with db.transaction(conn):
        (article_id,) = db.insert_get_id(conn, "articles", df)
    if article_id == 0:
        with db.transaction(conn):
            (article_id,) = conn.execute(
                "select rowid from articles where url = ? and article_hn_date = ?",
                (url, "TLRL-ADHOC"),
            ).fetchone()
    # send
    article_title, email_content, _ = _prepare_email(
        user_id=user_info.row_id, article_ids=[article_id]
    )
    send_mesage(email, f"Hacker News: '{article_title}'", email_content)
    return jsonify(status="success", url=url, email=email), 200


@api.route("/feedback")
def feedback_route():
    user_uuid = request.args.get("user_uuid")
    article_id = request.args.get("article_id")
    sentiment = request.args.get("sentiment")
    if user_uuid is None:
        print("CLIENT ERROR: No user_uuid provided")
        return "Bad Request", 400

    if article_id is None:
        print("CLIENT ERROR: No article_id provided")
        return "Bad Request", 400

    if sentiment is None:
        print("CLIENT ERROR: No sentiment provided")
        return "Bad Request", 400

    try:
        sentiment = int(sentiment)
    except ValueError:
        print("CLIENT ERROR: Bad value for sentiment")
        return "Bad Request", 400

    else:
        try:
            article_id = int(article_id)
        except ValueError:
            print("CLIENT ERROR: Bad value for article_id")
            return "Bad Request", 400
        else:
            conn = utils.get_connection()
            try:
                user_info = utils.get_user_info(conn=conn, user_uuid=user_uuid)
                if user_info is not None:
                    utils.set_feedback(
                        conn=conn,
                        col_name="sentiment",
                        article_id=article_id,
                        user_id=user_info.row_id,
                        sentiment=sentiment,
                    )
                else:
                    print(f"CLIENT ERROR: Unknown user {user_uuid}")
                    return "Bad Request", 400
            except Exception as e:
                print(f"ERROR: {e}")
                return "Internal Server Error", 500
            else:
                return redirect("/static/feedback.html")


@api.route("/unsubscribe")
def unsubscribe_route():
    user_uuid = request.args.get("user_uuid")
    if user_uuid is None:
        return "No user_uuid", 400
    conn = utils.get_connection()
    utils.unsubscribe(conn=conn, user_uuid=user_uuid)
    return redirect("/static/unsubscribed.html")


@api.route("/confirm")
def confirm_route():
    user_uuid = request.args.get("user_uuid")
    if user_uuid is None:
        return "No user_uuid", 400
    conn = utils.get_connection()
    user_info = utils.get_user_info(conn=conn, user_uuid=user_uuid)
    if user_info is not None:
        utils.confirm(conn=conn, email=user_info.email)
        return redirect("/static/subscription_confirmed.html")

    else:
        return "Unrecognized user_uuid", 400


@api.route("/subscribe")
def subscribe_route():
    email = request.args.get("email")
    num_articles_per_day = 1
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
    return redirect("/static/confirmation.html")


@api.route("/")
def home():
    return send_file("static/index.html")


@api.route("/static/<path:path>")
def send_static(path):
    return send_from_directory("static", path)


if __name__ == "__main__":
    api.run(host="0.0.0.0", port=5001)
