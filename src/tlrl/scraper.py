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

        scores = utils.get_scores(response.text)
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
            "readability_rms": readability_rms,
            "readability_sum": readability_sum,
            "readability_mean": readability_mean,
            "num_chars": len(response.text),
            "num_paragraphs": len(scores),
            "content": response.text,
            "summary": summary,
            "score": article_score,
        }


def ingest_date(url: str, date: str, max_num_articles: int) -> pd.DataFrame:
    response = requests.get(url, params={"day": date}, timeout=30)
    article_info = utils.get_article_info(response)[:max_num_articles]
    print(f"INFO: scraping {len(article_info)} links.")
    rows = []
    for link, title, article_score in article_info:
        if link.endswith(".pdf"):
            print(f"INFO: skipping {link} since it is likely a PDF.")
            continue
        print(f"INFO: scraping url={link} title={title} score={article_score}")
        try:
            row = ingest_impl(
                link=link, date=date, title=title, article_score=article_score
            )
        except Exception as e:
            print(f"ERR Failed to ingest {link}. Failed with:\n{e}")
        else:
            if row is not None:
                rows.append(row)
            else:
                print(f"WARN Got no data from {link}")

    return pd.DataFrame.from_dict(rows)


@prefect.task
def pipeline(max_num_articles: int = 30):
    conn = utils.get_connection()
    url = "https://news.ycombinator.com/front"
    date = utils.get_yesterday_mt()
    to_insert_df = ingest_date(url, date, max_num_articles=max_num_articles)
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
