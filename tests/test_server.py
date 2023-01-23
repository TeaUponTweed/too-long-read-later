import os
import pathlib
import time
import uuid
from typing import List

import pandas as pd
import pytest

from yesterdays_hackernews import cli, db, utils
from yesterdays_hackernews.api import api


@pytest.fixture
def db_loc(tmpdir: pathlib.Path) -> pathlib.Path:
    schema_loc = pathlib.Path(__file__).parent.resolve() / ".." / "schema.sql"
    cli.init_db_impl(db_file=tmpdir / "news.db", schema_file=schema_loc)
    return tmpdir / "news.db"


@pytest.fixture
def article_ids(db_loc) -> list[int]:
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
        for i in range(30)
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
                "user_id": str(uuid.uuid4()),
            },
            {
                "email": "asd2@asd.asd",
                "confirmed": 0,
                "num_articles_per_day": 1,
                "user_id": str(uuid.uuid4()),
            },
            {
                "email": "asd3@asd.asd",
                "confirmed": 1,
                "num_articles_per_day": 0,
                "user_id": str(uuid.uuid4()),
            },
            {
                "email": "asd4@asd.asd",
                "confirmed": 1,
                "num_articles_per_day": 1,
                "user_id": str(uuid.uuid4()),
            },
            {
                "email": "asd5@asd.asd",
                "confirmed": 1,
                "num_articles_per_day": 13,
                "user_id": str(uuid.uuid4()),
            },
        ]
    )
    print(user_df)
    with db.transaction(conn):
        user_ids = db.insert(conn, "users", user_df)
    return user_ids


def test_query(db_loc, article_ids, user_ids):
    q_potential_article_queries = """
    select articles.rowid as article_id, users.rowid as user_id
    from articles
    cross join users
    where article_hn_date = '2020-01-02'
    and not exists (select * from feedback where articles.rowid = feedback.article_id and users.rowid = feedback.user_id);
    """


# TODO
# add users with rest
# add feed back with rest
# test ingest on a fixed article
#
