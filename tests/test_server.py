# from flask_testing import TestCase
import pathlib
from yesterdays_hackernews.api import api
from yesterdays_hackernews import utils
from typing import List
from yesterdays_hackernews import cli, db
import uuid
import pytest
import os
import pandas as pd
import time
# from yesterdays_hackernews import app

@pytest.fixture
def db_loc(tmpdir: pathlib.Path) -> pathlib.Path:
    schema_loc = pathlib.Path(__file__).parent.resolve() / '..' / 'schema.sql'
    cli.init_db_impl(db_file = tmpdir / "news.db", schema_file=schema_loc)
    return tmpdir / "news.db"

@pytest.fixture
def article_ids(db_loc) -> list[int]:
    article_df = pd.DataFrame.from_dict({
        "article_hn_date": f"2020-{str(MM).zfill(2)}-{str(DD).zfill(2)}",
        'scrape_time': int(time.time()),
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
    for MM in range(1,13)
    for DD in range(1,29)
    )
    # conn = sqlite3.connect(db_loc, isolation_level=None)
    conn = utils.get_connection(str(db_loc))
    with db.transaction(conn):
        article_ids = db.insert_get_id(conn, 'articles', article_df)
    return article_ids
    # print(db_loc)
    # import pdb; pdb.set_trace()


@pytest.fixture
def user_ids(db_loc: pathlib.Path) -> List[int]:
    conn = utils.get_connection(str(db_loc))
    user_df = pd.DataFrame.from_dict(
        [
            {'email': 'asd1@asd.asd', "confirmed": 0, "num_articles_per_day": 0 , "user_id": str(uuid.uuid4())},
            {'email': 'asd2@asd.asd', "confirmed": 0, "num_articles_per_day": 1 , "user_id": str(uuid.uuid4())},
            {'email': 'asd3@asd.asd', "confirmed": 1, "num_articles_per_day": 0 , "user_id": str(uuid.uuid4())},
            {'email': 'asd4@asd.asd', "confirmed": 1, "num_articles_per_day": 1 , "user_id": str(uuid.uuid4())},
            {'email': 'asd5@asd.asd', "confirmed": 1, "num_articles_per_day": 13, "user_id": str(uuid.uuid4())},
        ]
    )
    print(user_df)
    with db.transaction(conn):
        user_ids = db.insert(conn, 'users', user_df)
    return user_ids

def test_query(db_loc, article_ids, user_ids):
    # conn = utils.get_connection(str(db_loc))
    print(db_loc)
    import pdb; pdb.set_trace()
    # goal is to find all articles which have been sent 
    '''
    -- first get all articles from yesterday
    with date_articles as (
        select rowid from articles
        where date = '2020-01-02'
    ), potential_feedback as (
    select (date_articles.rowid as article_id, users.rowid as user_id)
    from users
    cross join date_articles
    )
    select potential_feedback.user_id, potential_feedback.article_id
    from potential_feedback
    where article_id not in (fee)
    select potential_feedback.article_id, potential_feedback.user_id
    from potential_feedback
    where not exists select (* from feedback where potential_feedback.article_id = feedback.article_id)
    from date_articles as A, potential_feedback as B
    '''
    '''
    with date_articles as (

    ), potential_feedback as (
        select date_articles.rowid as article_id, users.rowid as user_id
        from users
        cross join date_articles;
    )
    select * from potential_feedback;
    select articles.rowid as article_id, users.rowid as user_id
    from articles
    cross join users
    where article_hn_date = '2020-01-02'
    and not exists (select * from feedback where articles.rowid = feedback.article_id);

    select potential_feedback.user_id, potential_feedback.article_id
    from potential_feedback
    from potential_feedback
    where not exists select (* from feedback where potential_feedback.article_id = feedback.article_id)
    '''
    '''
    select count(*) -- articles.rowid as article_id, users.rowid as user_id
    from articles
    cross join users
    where article_hn_date = '2020-01-02'
    and not exists (select * from feedback where articles.rowid = feedback.article_id and users.rowid = feedback.user_id);
    '''
# TODO
# add fake article data
# add users with rest
# add feed back with rest
