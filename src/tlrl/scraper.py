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


def ingest_impl(
    link: str,
    date: str,
    title: Optional[str] = None,
    article_score: Optional[int] = None,
) -> Optional[dict]:
    try:
        response = utils.get_page_response(link)
    except Exception as e:
        print(f"ERR Failed to scrape {link}. Failed with error:\n{str(e)}")
        return
    else:
        if response.status_code != 200:
            print(f"ERR {link}. returned code {response.status_code}")
            return
        inferred_title, _, summary = utils.extract_content(response.text)
        if title is None:
            title = inferred_title

        return {
            "article_hn_date": date,
            "scrape_time": int(time.time()),
            "title": title,
            "url": link,
            "content": response.text,
            "summary": summary,
            "score": article_score,
        }

def ingest_date(url: str, date: str) -> pd.DataFrame:
    response = requests.get(url, params={"day": date}, timeout=30)
    article_info = utils.get_article_info(response)
    print(f"INFO: scraping {len(article_info)} links.")
    rows = []
    for link, title, article_score in article_info:
        if link.endswith(".pdf"):
            print(f"INFO: skipping {link} since it is likely a PDF.")
            continue
        print(f"INFO: scraping url={link} title={title} score={article_score}")

        rows.append(
            ingest_impl(link=link, date=date, title=title, article_score=article_score)
        )

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
