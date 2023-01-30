import math
import time
from datetime import timedelta
from typing import Optional

import pandas as pd
import pendulum
import prefect
import requests
from prefect import schedules

from tlrl import db, utils


def ingest_impl(link: str, date: str, title: Optional[str] = None) -> dict:
    try:
        inferred_title, html, scores = utils.extract_content(
            utils.get_page_response(link).text, url=link
        )
    except Exception as e:
        print(f"ERR Failed to scrape {link}. Failed with error: {str(s)}")
        return {
            "article_hn_date": date,
            "scrape_time": int(time.time()),
            "title": title,
            "url": date,
            "content": None,
            "readability_rms": None,
            "readability_sum": None,
            "readability_mean": None,
            "num_chars": None,
            "num_paragraphs": None,
        }
    else:
        if title is None:
            title = inferred_title
        if len(scores) > 0:
            readability_rms = math.sqrt(
                sum(score**2 for score in scores) / len(scores)
            )
            readability_sum = sum(scores)
            readability_mean = sum(scores) / len(scores)
        else:
            readability_rms = 0
            readability_sum = 0
            readability_mean = 0

        return {
            "article_hn_date": date,
            "scrape_time": int(time.time()),
            "title": title,
            "url": link,
            "content": html,
            "readability_rms": readability_rms,
            "readability_sum": readability_sum,
            "readability_mean": readability_mean,
            "num_chars": len(html),
            "num_paragraphs": len(scores),
        }


def ingest_date(url: str, date: str) -> pd.DataFrame:
    response = requests.get(url, params={"day": date})
    links_and_title = utils.get_articles_links_and_title(response)
    rows = []
    for link, title in links_and_title:
        rows.append(ingest_impl(link=link, date=date, title=title))

    return pd.DataFrame.from_dict(rows)


@prefect.task
def pipeline():
    conn = utils.get_connection()
    url = "https://news.ycombinator.com/front"
    date = utils.get_yesterday_mt()
    to_insert_df = ingest_date(url, date)
    with db.transaction(conn):
        db.insert_get_id(conn, "articles", to_insert_df)


if __name__ == "__main__":
    clock = schedules.clocks.IntervalClock(
        start_date=pendulum.datetime(2019, 1, 1, hour=3, tz=utils.MT),
        interval=timedelta(days=1),
    )
    schedule = schedules.Schedule(clocks=[clock])
    with prefect.Flow("scrape_tlrl", schedule=schedule) as flow:
        pipeline()
    flow.run()
