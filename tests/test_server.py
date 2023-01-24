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
def num_articles_per_day() -> int:
    return 30

@pytest.fixture
def db_loc(tmpdir: pathlib.Path) -> pathlib.Path:
    schema_loc = pathlib.Path(__file__).parent.resolve() / ".." / "schema.sql"
    cli.init_db_impl(db_file=tmpdir / "news.db", schema_file=schema_loc)
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
                "user_uuid": str(uuid.uuid4()),
            },
            {
                "email": "asd2@asd.asd",
                "confirmed": 0,
                "num_articles_per_day": 1,
                "user_uuid": str(uuid.uuid4()),
            },
            {
                "email": "asd3@asd.asd",
                "confirmed": 1,
                "num_articles_per_day": 0,
                "user_uuid": str(uuid.uuid4()),
            },
            {
                "email": "asd4@asd.asd",
                "confirmed": 1,
                "num_articles_per_day": 1,
                "user_uuid": str(uuid.uuid4()),
            },
            {
                "email": "asd5@asd.asd",
                "confirmed": 1,
                "num_articles_per_day": 13,
                "user_uuid": str(uuid.uuid4()),
            },
        ]
    )
    with db.transaction(conn):
        user_ids = db.insert_get_id(conn, "users", user_df)
    return user_ids


def test_query(db_loc, article_ids, user_ids, num_articles_per_day):
    conn = utils.get_connection(str(db_loc))
    articles_and_users = utils.get_articles_without_feedback(conn=conn, date='2020-01-01')
    these_article_ids,these_user_ids = map(lambda x: sorted(set(x)), zip(*articles_and_users))
    assert len(articles_and_users) == num_articles_per_day*len(user_ids)
    os.environ["DB_FILE_LOC"] = str(db_loc)
    for user_id in user_ids:
        user_info = utils.get_user_info(conn,row_id=user_id)
        user_info2 = utils.get_user_info(conn,user_uuid=user_info.user_uuid)
        user_info3 = utils.get_user_info(conn,email=user_info.email)
        assert user_info == user_info2 == user_info3
        for article_id in these_article_ids[:5]:
            for col_name in 'sentiment','format_quality','should_format':
                for sentiment in [-1,1]:
                    response = api.test_client().get(f'/feedback/{col_name}?user_uuid={user_info.user_uuid}&article_id={article_id}&sentiment={sentiment}')
                    with db.transaction(conn):
                        ret = conn.execute(f"select {col_name} from feedback where user_id = ? and article_id = ?", (user_info.row_id, article_id)).fetchone()
                        # conn.execute(f"select article_id,user_id from feedback").fetchall()
                        assert response.status_code == 200
                        assert ret[0] == sentiment

    other_articles_and_users = utils.get_articles_without_feedback(conn=conn, date='2020-01-01')
    assert len(other_articles_and_users) == (num_articles_per_day-5)*len(user_ids)


# TODO
# add users with rest
# unsubscribe
# update sub number
# test ingest on a fixed article
