import os
import pathlib
import urllib

import pytest

from tlrl import api, cli, db, utils
from tlrl.scraper import pipeline


@pytest.fixture
def db_loc2(tmpdir: pathlib.Path) -> pathlib.Path:
    schema_loc = pathlib.Path(__file__).parent.resolve() / ".." / "schema.sql"
    cli.init_db_impl(db_file=tmpdir / "news.db", schema_file=schema_loc)
    os.environ["DB_FILE_LOC"] = str(tmpdir / "news.db")
    return tmpdir / "news.db"


@pytest.mark.slow
def test_scrape(db_loc2: pathlib.Path):
    pipeline.run(2)
    yesterday = utils.get_yesterday_mt()
    conn = utils.get_connection()
    with db.transaction(conn):
        (cnt,) = conn.execute(
            "select count(*) from articles where article_hn_date = ?", (yesterday,)
        ).fetchone()

    assert cnt > 0


def test_subscribe(db_loc2: pathlib.Path):
    # add 2 confirmed users
    conn = utils.get_connection()
    for email in "asd1@asd.asd", "asd2@asd.asd":
        user = utils.get_user_info(conn=conn, email=email)
        assert user is None
        subscribe_url = "/subscribe?" + urllib.parse.urlencode(
            {
                "email": email,
                "num_articles_per_day": 1,
            }
        )
        response = api.api.test_client().get(subscribe_url)
        assert response.status_code == 302
        user = utils.get_user_info(conn=conn, email=email)
        assert user is not None
        assert user.email == email
        assert not user.confirmed
        bad_confirm_url = "/confirm?" + urllib.parse.urlencode(
            {
                "user_uuid": "Not right",
            }
        )
        response = api.api.test_client().get(bad_confirm_url)
        assert response.status_code == 400

        confirm_url = "/confirm?" + urllib.parse.urlencode(
            {
                "user_uuid": user.user_uuid,
            }
        )
        response = api.api.test_client().get(confirm_url)
        assert response.status_code == 302
        user = utils.get_user_info(conn=conn, email=email)
        assert user.confirmed
