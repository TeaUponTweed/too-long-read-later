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
    pipeline.run()
    yesterday = utils.get_yesterday_mt()
    conn = utils.get_connection()
    with db.transaction(conn):
        (cnt,) = conn.execute(
            "select count(*) from articles where article_hn_date = ?", (yesterday,)
        ).fetchone()

    assert cnt > 0
    # # add 2 confirmed users
    # for email in "asd1@asd.asd", "asd2@asd.asd":
    #     subscribe_url = "/subscribe?" + urllib.parse.urlencode(
    #         {
    #             "email": email,
    #             "num_articles_per_day": 1,
    #         }
    #     )
    #     response = api.test_client().get(sub_url)
    #     assert response.status_code == 200
    #     confirm_url = "/confirm?" + urllib.parse.urlencode(
    #         {
    #             "email": email,
    #         }
    #     )
    #     response = api.test_client().get(confirm_url)
    #     assert response.status_code == 200
