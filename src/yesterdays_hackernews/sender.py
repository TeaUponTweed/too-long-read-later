import itertools
import random
import sqlite3
from typing import Iterator, List, Optional, Tuple

import prefect

from yesterdays_hackernews import db, utils
from yesterdays_hackernews.send import send_mesage


def _prepare_email(
    user_id: int, article_ids: List[int], inline: bool = True
) -> Optional[Tuple[str, str, int]]:
    # TODO eventually content curation and inlining decisions will go here. Ideally this would not have to know about the database....
    conn = utils.get_connection()
    if len(article_ids) == 0:
        return None
    else:
        article_id = random.choice(article_ids)
    with db.transaction(conn):
        (article_title, article_content_html, article_url) = conn.execute(
            "select title,content, url from articles where rowid = ?", (article_id,)
        ).fetchone()
    user_info = utils.get_user_info(conn=conn, row_id=user_id)
    if inline:
        html = utils.apply_template(
            "email_template.html",
            {
                "article_title": article_title,
                "article_url": article_url,
                "article_body": article_content_html,
                "user_uuid": user_info.user_uuid,
            },
        )
    else:
        html = utils.apply_template(
            "email_template_no_inline.html",
            {
                "article_title": article_title,
                "article_url": article_url,
                "user_uuid": user_info.user_uuid,
            },
        )
    return article_title, html, article_id


def gen_emails_to_send(
    conn: Optional[sqlite3.Connection] = None, date: Optional[str] = None
) -> Iterator[Tuple[str, str, str, int, int]]:
    if date is None:
        date = utils.get_yesterday_mt()
    if conn is None:
        conn = utils.get_connection()
    # TODO this can all be done in sql, het HCB to help
    # TODO can this fail? add logging
    with db.transaction(conn):
        to_send_user_ids = conn.execute(
            """
            with send_count as (
            select user_id,count(*) as num_sent
            from feedback
            join articles on articles.rowid = feedback.article_id
            where articles.article_hn_date = ?
            group by user_id
            )
            select users.rowid,email from users
            left join send_count on users.rowid = send_count.user_id
            where users.confirmed and (send_count.num_sent < users.num_articles_per_day)
        """,
            (date,),
        )
    to_send_user_ids = dict(to_send_user_ids)
    paired_ids = utils.get_articles_without_feedback(conn, date)
    if len(paired_ids) == 0 and to_send_user_ids > 0:
        print("WARNL failed to find any articles to send!")
    for user_id, ids in itertools.groupby(
        sorted(paired_ids, key=lambda x: x[1]), key=lambda x: x[1]
    ):
        if user_id not in to_send_user_ids:
            print("ERR: failed to get email for user which should have one sent....")
            continue
        else:
            email = to_send_user_ids[user_id]
        article_ids, _ = zip(*ids)
        ret = _prepare_email(user_id=user_id, article_ids=article_ids)
        if ret is not None:
            yield (email, *ret, user_id)


@prefect.task
def pipeline():
    for email, title, content, article_id, user_id in gen_emails_to_send():
        send_mesage(email, f"Hacker News: '{title}'", content)
        with db.transaction(conn):
            conn.execute(
                "insert into feedback(user_id,article_id) values (?,?)",
                (user_id, article_id),
            )


if __name__ == "__main__":
    # check 5 minutes past the hour
    schedule = prefect.schedules.CronSchedule(cron="5 * * * *")
    with prefect.Flow("yesterdays_hackernews", schedule=schedule) as flow:
        pipeline()
    flow.run()
