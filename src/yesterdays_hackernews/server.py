import uuid

from flask import Flask, request

app = Flask(__name__)


@app.route("/feedback/bad_inlining")
def bad_inlining():
    userid = request.args.get("userid")
    article_id = request.args.get("article_id")
    # Logic to handle bad inlining feedback goes here
    return "Bad inlining feedback received for user ID {} and article ID {}".format(
        userid, article_id
    )


@app.route("/feedback/dont_inline")
def dont_inline():
    userid = request.args.get("userid")
    article_id = request.args.get("article_id")
    # Logic to handle "don't inline" feedback goes here
    return "Don't inline feedback received for user ID {} and article ID {}".format(
        userid, article_id
    )


@app.route("/feedback/do_inline")
def do_inline():
    userid = request.args.get("userid")
    article_id = request.args.get("article_id")
    # Logic to handle "do inline" feedback goes here
    return "Do inline feedback received for user ID {} and article ID {}".format(
        userid, article_id
    )


@app.route("/feedback/interesting")
def interesting():
    userid = request.args.get("userid")
    article_id = request.args.get("article_id")
    # Logic to handle "interesting" feedback goes here
    return "Interesting feedback received for user ID {} and article ID {}".format(
        userid, article_id
    )


@app.route("/feedback/not_interesting")
def not_interesting():
    userid = request.args.get("userid")
    article_id = request.args.get("article_id")
    # Logic to handle "not interesting" feedback goes here
    return "Not interesting feedback received for user ID {} and article ID {}".format(
        userid, article_id
    )


@app.route("/unsubscribe")
def unsubscribe():
    userid = request.args.get("userid")
    # Logic to handle unsubscription goes here
    return "Unsubscribed user with ID {}".format(userid)


@app.route("/subscribe")
def subscribe():
    userid = request.args.get("userid")
    # Logic to handle subscription goes here
    return "Subscribed user with ID {}".format(userid)


@app.route("/set_hn_digest_num")
def set_hn_digest_num():
    userid = request.args.get("userid")
    num_emails = request.args.get("num_emails")
    # Logic to handle setting the number of HN digest emails goes here
    return "Set HN digest email frequency to {} for email {}".format(num_emails, email)


if __name__ == "__main__":
    app.run()
