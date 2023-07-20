import itertools
import random
import sqlite3
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

import prefect

from tlrl import db, utils
from tlrl.send import send_mesage


@dataclass
class Article:
    title: str
    summary: str
    url: str
    artice_id: int

def get_articles(conn: sqlite3.Connection, date: str) -> list[Article]:
    with db.transaction(conn):
        article_data = conn.execute(
            """select rowid, title,summary, url from articles
            where article_hn_date = ?
            and summary is not null
            """, (date,)
        ).fetchall()

    articles = [
        Article(
            title=article_title,
            summary=article_summary,
            url=article_url,
            artice_id=artice_id
        )
        for artice_id, article_title, article_summary, article_url in article_data
    ]
    return articles

def _prepare_email(
    user_id: int, articles: Optional[List[Article]]
) -> str:
    # TODO eventually content curation and inlining decisions will go here. Ideally this would not have to know about the database....
    conn = utils.get_connection()

    user_info = utils.get_user_info(conn=conn, row_id=user_id)
    if user_info is not None:
        return utils.apply_template(
            "email_template.html",
            {
                "articles": articles,
                "user_uuid": user_info.user_uuid,
            },
        )
    else:
        print(f"WARN: Cannot prepre email. Unknown user_id {user_id}")
        return None



def gen_emails_to_send(
    conn: Optional[sqlite3.Connection] = None, date: Optional[str] = None
) -> Iterator[Tuple[str, str]]:
    if date is None:
        date = utils.get_yesterday_mt()
    if conn is None:
        conn = utils.get_connection()

    with db.transaction(conn):
        subscribed_users = conn.execute(
            """select users.rowid,users.email from users
               where users.confirmed and users.num_articles_per_day > 0"""
        ).fetchall()

    # with db.transaction(conn):
    #     q = """select rowid from articles
    #            where article_hn_date = ?"""
    #     print(q)
    #     print(date)
    #     article_ids = conn.execute(
    #         """select rowid from articles
    #            where article_hn_date = ?""", (date,)
    #     ).fetchall()
    articles = get_articles(conn=conn, date=date)

    if len(subscribed_users) == 0:
        print("WARN: No users subscribed")
        return

    if len(articles) == 0:
        print("WARN: No articles to send")
        return

    for user_id, user_email in subscribed_users:
        email_content = _prepare_email(user_id=user_id, articles=articles)
        if email_content is not None:
            yield (user_email, email_content)


@prefect.task
def pipeline():
    conn = utils.get_connection()
    ix = utils.hours_since_6am_mt()
    if not (ix == 0):
        print("Only runs at 6AM MT")
        return
    conn = utils.get_connection()
    date = utils.get_yesterday_mt()
    for email,  content in gen_emails_to_send(conn=conn, date=date):
        send_mesage(email, f"Yesderdays Newsletter, Today! {date}'", content)


if __name__ == "__main__":
    # check 5 minutes past the hour
    schedule = prefect.schedules.CronSchedule(cron="5 * * * *")
    with prefect.Flow("tlrl-sender", schedule=schedule) as flow:
        pipeline()
    flow.run()
