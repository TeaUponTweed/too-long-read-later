import itertools
import random
import sqlite3
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

import prefect

from tlrl import db, utils
from tlrl.send import send_mesage


def _prepare_email(user_id: int, articles: Optional[List[utils.Article]]) -> str:
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

    articles = utils.get_articles(conn=conn, date=date)
    subscribed_users = utils.get_subscribed_users(conn=conn)

    if len(subscribed_users) == 0:
        print("WARN: No users subscribed")
        return

    if len(articles) == 0:
        print("WARN: No articles to send")
        return

    for user in subscribed_users:
        email_content = _prepare_email(user_id=user.row_id, articles=articles)
        if email_content is not None:
            yield (user.email, email_content)


@prefect.task
def pipeline(force_run_now: bool = False):
    conn = utils.get_connection()
    ix = utils.hours_since_5am_mt()
    if ix == 0 or force_run_now:
        conn = utils.get_connection()
        date = utils.get_yesterday_mt()
        for email, content in gen_emails_to_send(conn=conn, date=date):
            send_mesage(email, f"Yesderdays News, Today! {date}'", content)
    else:
        print("Only runs at 6AM MT")


if __name__ == "__main__":
    # check 5 minutes past the hour
    schedule = prefect.schedules.CronSchedule(cron="5 * * * *")
    with prefect.Flow("tlrl-sender", schedule=schedule) as flow:
        pipeline()
    flow.run()
