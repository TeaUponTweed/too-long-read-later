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


def get_hn_stories_for_date(date: str, max_stories: int) -> list:
    """Get top HN stories for a specific date using HN Search API"""
    url = "https://hn.algolia.com/api/v1/search_by_date"
    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>={get_date_timestamp(date)},created_at_i<{get_date_timestamp(date) + 86400}",
        "hitsPerPage": max_stories,
        "sortBy": "popularity",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    stories = []
    for hit in data.get("hits", []):
        if hit.get("url"):  # Only include stories with URLs
            stories.append((hit["url"], hit.get("title", ""), hit.get("points", 0)))

    return stories


def get_date_timestamp(date_str: str) -> int:
    """Convert date string to Unix timestamp"""
    dt = pendulum.parse(date_str)
    return int(dt.timestamp())


def url_already_exists(conn, url: str) -> bool:
    """Check if URL already exists in database"""
    query = "SELECT COUNT(*) FROM articles WHERE url = ?"
    cursor = conn.cursor()
    cursor.execute(query, (url,))
    count = cursor.fetchone()[0]
    return count > 0


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
        inferred_title, summary = utils.extract_content(response.text)
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


def ingest_date(date: str, max_num_articles: int) -> int:
    """Ingest articles for a date and return count of successful inserts"""
    conn = utils.get_connection()

    print(f"INFO: Getting top {max_num_articles} HN stories for {date}")
    article_info = get_hn_stories_for_date(date, max_num_articles)
    print(f"INFO: Found {len(article_info)} stories to process")

    successful_inserts = 0

    for link, title, article_score in article_info:
        # Check if URL already exists
        if url_already_exists(conn, link):
            print(f"INFO: Skipping {link} - already exists in database")
            continue

        if link.endswith(".pdf"):
            print(f"INFO: Skipping {link} since it is likely a PDF.")
            continue

        print(f"INFO: Processing url={link} title={title} score={article_score}")

        try:
            row = ingest_impl(
                link=link, date=date, title=title, article_score=article_score
            )
        except Exception as e:
            print(f"ERR Failed to ingest {link}. Failed with:\n{e}")
            continue

        if row is not None:
            try:
                # Insert single row immediately
                row_df = pd.DataFrame([row])
                with db.transaction(conn):
                    inserted_ids = db.insert_get_id(conn, "articles", row_df)
                    if inserted_ids and inserted_ids[0]:
                        successful_inserts += 1
                        print(
                            f"INFO: Successfully inserted article {inserted_ids[0]} for {link}"
                        )
                    else:
                        print(f"WARN: Failed to get insert ID for {link}")
            except Exception as e:
                print(f"ERR Failed to insert {link} into database: {e}")
        else:
            print(f"WARN Got no data from {link}")

        # Rate limiting
        time.sleep(0.3)

    return successful_inserts


@prefect.task
def pipeline(max_num_articles: int = 30, date: Optional[str] = None):
    if date is None:
        date = utils.get_yesterday_mt()

    successful_count = ingest_date(date, max_num_articles=max_num_articles)
    print(f"INFO: Successfully processed {successful_count} articles for {date}")


if __name__ == "__main__":
    clock = schedules.clocks.IntervalClock(
        start_date=pendulum.datetime(2019, 1, 1, hour=3, tz=utils.MT),
        interval=timedelta(days=1),
    )
    schedule = schedules.Schedule(clocks=[clock])
    with prefect.Flow("scrape_tlrl", schedule=schedule) as flow:
        pipeline()
    flow.run()
