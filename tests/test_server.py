# from flask_testing import TestCase
import pathlib
from yesterdays_hackernews.server import api
from yesterdays_hackernews import cli
import pytest
import os
import pandas as pd
from yesterdays_hackernews import app

@pytest.fixture
def db_loc(tmpdir: pathlib.Path) -> pathlib.Path:
    schema_loc = pathlib.Path(__file__).parent.resolve() / '..' / 'schema.sql'
    init_db_impl(db_file = tmpdir / "news.db", schema_file=schema_loc)
    return tmpdir / "news.db"

@pytest.fixture
def article_ids(db_loc) -> list[int]:
    df = pd.DataFrame.from_dict({
        "scrape_date" f"2020-{str(MM).zfill(2)}-{str(DD).zfill(2)}",
        "title" "asd",
        "url" "not.a.url",
        "content" "",
        "readability_rms" 1,
        "readability_sum" 1,
        "readability_mean" 1,
        "num_chars" 1,
        "num_paragraphs" 1,
    }
    for MM in range(1,13)
    for DD in range(1,28)
    )
    conn = sqlite3.connect(db_loc, isolation_level=None)
    with db.transaction(conn)



# TODO
# add fake article data
# add users with rest
# add feed back with rest
