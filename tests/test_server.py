import os
import pathlib
import random
import time
import urllib
import uuid
from typing import List

import pandas as pd
import pytest

from tlrl import cli, db, sender, utils
from tlrl.api import api


@pytest.fixture
def num_articles_per_day() -> int:
    return 30


@pytest.fixture
def db_loc(tmpdir: pathlib.Path) -> pathlib.Path:
    schema_loc = pathlib.Path(__file__).parent.resolve() / ".." / "schema.sql"
    cli.init_db_impl(db_file=tmpdir / "news.db", schema_file=schema_loc)
    os.environ["DB_FILE_LOC"] = str(tmpdir / "news.db")
    os.environ["EMAIL_ADDRESS"] = "TEST_DO_NOT_SEND"
    return tmpdir / "news.db"


@pytest.fixture
def article_ids(db_loc, num_articles_per_day) -> list[int]:
    article_df = pd.DataFrame.from_dict(
        {
            "article_hn_date": f"2020-{str(MM).zfill(2)}-{str(DD).zfill(2)}",
            "scrape_time": int(time.time()),
            "title": str(i),
            "url": f"not.a.url{i}",
            "content": "",
            "readability_rms": 1,
            "readability_sum": 1,
            "readability_mean": 1,
            "num_chars": 1,
            "num_paragraphs": 1,
        }
        for i in range(num_articles_per_day)
        for MM in range(1, 13)
        for DD in range(1, 29)
    )
    conn = utils.get_connection(str(db_loc))
    with db.transaction(conn):
        article_ids = db.insert_get_id(conn, "articles", article_df)
    return article_ids


@pytest.fixture
def user_ids(db_loc: pathlib.Path) -> List[int]:
    conn = utils.get_connection(str(db_loc))
    user_df = pd.DataFrame.from_dict(
        [
            {
                "email": "asd1@asd.asd",
                "confirmed": 0,
                "num_articles_per_day": 0,
            },
            {
                "email": "asd2@asd.asd",
                "confirmed": 0,
                "num_articles_per_day": 1,
            },
            {
                "email": "asd3@asd.asd",
                "confirmed": 1,
                "num_articles_per_day": 0,
            },
            {
                "email": "asd4@asd.asd",
                "confirmed": 1,
                "num_articles_per_day": 13,
            },
            {
                "email": "asd5@asd.asd",
                "confirmed": 1,
                "num_articles_per_day": 13,
            },
        ]
    )
    for _, row in user_df.iterrows():
        subscibe_url = "/subscribe?" + urllib.parse.urlencode(
            {
                "email": str(row.email),
                "num_articles_per_day": int(row.num_articles_per_day),
            }
        )
        response = api.test_client().get(subscibe_url)
        assert response.status_code == 200
        user_info = utils.get_user_info(conn=conn, email=row.email)
        if row.confirmed:
            confirm_url = "/confirm?" + urllib.parse.urlencode(
                {
                    "user_uuid": str(user_info.user_uuid),
                }
            )
            response = api.test_client().get(confirm_url)
            assert response.status_code == 200
            with db.transaction(conn):
                (confirmed,) = conn.execute(
                    "select confirmed from users where email = ?", (row.email,)
                ).fetchone()
            assert confirmed
        else:
            with db.transaction(conn):
                (confirmed,) = conn.execute(
                    "select confirmed from users where email = ?", (row.email,)
                ).fetchone()
            assert not confirmed

    conn = utils.get_connection(str(db_loc))
    with db.transaction(conn):
        res = conn.execute(f"select rowid from users").fetchall()
    user_ids = [int(user_id) for user_id, in res]
    assert len(user_ids) == user_df.shape[0]
    return user_ids


def test_api(db_loc, article_ids, user_ids, num_articles_per_day):
    # feedback
    conn = utils.get_connection(str(db_loc))
    date = "2020-01-01"
    articles_and_users = utils.get_articles_without_feedback(conn=conn, date=date)
    these_article_ids, these_user_ids = map(
        lambda x: sorted(set(x)), zip(*articles_and_users)
    )
    assert len(articles_and_users) == num_articles_per_day * len(user_ids)
    for user_id in user_ids:
        user_info = utils.get_user_info(conn, row_id=user_id)
        user_info2 = utils.get_user_info(conn, user_uuid=user_info.user_uuid)
        user_info3 = utils.get_user_info(conn, email=user_info.email)
        assert user_info == user_info2 == user_info3
        for article_id in these_article_ids[:5]:
            for col_name in "sentiment", "format_quality", "should_format":
                for sentiment in [-1, 1]:
                    response = api.test_client().get(
                        f"/feedback/{col_name}?user_uuid={user_info.user_uuid}&article_id={article_id}&sentiment={sentiment}"
                    )
                    with db.transaction(conn):
                        ret = conn.execute(
                            f"select {col_name} from feedback where user_id = ? and article_id = ?",
                            (user_info.row_id, article_id),
                        ).fetchone()
                    # conn.execute(f"select article_id,user_id from feedback").fetchall()
                    assert response.status_code == 200
                    assert ret[0] == sentiment

    other_articles_and_users = utils.get_articles_without_feedback(conn=conn, date=date)
    assert len(other_articles_and_users) == (num_articles_per_day - 5) * len(user_ids)

    emails = list(sender.gen_emails_to_send(date=date))
    assert len(emails) == 2
    assert sorted([emails[0][0], emails[1][0]]) == [
        "asd4@asd.asd",
        "asd5@asd.asd",
    ]
    # updating article number
    user_info = utils.get_user_info(conn=conn, row_id=user_ids[-1])
    with db.transaction(conn):
        (num_articles,) = conn.execute(
            "select num_articles_per_day from users where rowid = ?",
            (user_info.row_id,),
        ).fetchone()
    assert num_articles > 0

    unsub_url = "/unsubscribe?" + urllib.parse.urlencode(
        {"user_uuid": str(user_info.user_uuid)}
    )
    response = api.test_client().get(unsub_url)
    assert response.status_code == 200
    with db.transaction(conn):
        (num_articles,) = conn.execute(
            "select num_articles_per_day from users where rowid = ?",
            (user_info.row_id,),
        ).fetchone()
    assert num_articles == 0

    sub_url = "/subscribe?" + urllib.parse.urlencode(
        {"email": str(user_info.email), "num_articles_per_day": 11}
    )
    response = api.test_client().get(sub_url)
    assert response.status_code == 200
    with db.transaction(conn):
        (num_articles,) = conn.execute(
            "select num_articles_per_day from users where rowid = ?",
            (user_info.row_id,),
        ).fetchone()
    assert num_articles == 11


def test_ingest(db_loc: pathlib.Path):
    link = "test_post_html"
    with open("tests/test_post.html") as fi:
        html = fi.read()
    title, text, summary = utils.extract_content(html, url=link)
    html = utils.apply_template(
        "email_template.html",
        {
            "article_title": title,
            "article_url": "test_post_html",
            "article_body": text,
            "article_id": -1,
        },
    )
    _ = utils.apply_template(
        "email_template_no_inline.html",
        {
            "article_title": title,
            "article_url": "test_post_html",
            "user_uuid": str(uuid.uuid4()),
            "article_id": -1,
        },
    )
    _ = utils.apply_template(
        "email_template.html",
        {
            "article_title": title,
            "article_url": link,
            "article_body": text,
            "user_uuid": str(uuid.uuid4()),
            "article_id": -1,
        },
    )
