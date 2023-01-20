import math
import sqlite3

import click
import pandas as pd
import requests

from yesterdays_hackernews import utils, db


@click.group()
def cli():
    pass


@cli.command("cat-link")
@click.argument("link", required=True, type=str)
def cat_link(link: str):
    title, html, _ = utils.extract_link(link)
    html = utils.apply_template(
        "email_template.html",
        {"article_title": title, "article_url": link, "article_body": html},
    )
    print(html)


def ingest_impl(url: str, date: str) -> pd.DataFrame:
    response = requests.get(url, params={"day": date})
    links_and_title = utils.get_articles_links_and_title(response)
    rows = []
    for link, title in links_and_title:
        _, html, scores = utils.extract_link(link)
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

        rows.append(
            {
                "scrape_date": date,
                "title": title,
                "url": link,
                "content": html,
                "readability_rms": readability_rms,
                "readability_sum": readability_sum,
                "readability_mean": readability_mean,
                "num_chars": len(html),
                "num_paragraphs": len(scores),
            }
        )

    return pd.DataFrame.from_dict(rows)


@cli.command("ingest")
@click.option("-d", "--db-file", required=True, type=str)
@click.option("--date", required=True, type=str)
def ingest_hn_date(db_file: str, date: str):
    conn = sqlite3.connect(db_file, isolation_level=None)
    url = "https://news.ycombinator.com/front"

    conn = sqlite3.connect(db_file, isolation_level=None)
    to_insert_df = ingest_impl(url, date)
    with db.transaction(conn):
        db.insert_get_id(conn, "articles", to_insert_df)


def init_db_impl(db_file: str, schema_file: str) -> str:
    conn = sqlite3.connect(db_file, isolation_level=None)
    conn.execute("pragma journal_mode=wal")
    with open(schema_file) as fi:
        schema = fi.read()
        with db.transaction(conn):
            conn.executescript(schema)
        return schema


@cli.command("init")
@click.option("-d", "--db-file", required=True, type=str)
@click.option("-s", "--schema-file", required=True, type=str)
def init_db(db_file: str, schema_file: str):
    schema = init_db_impl(db_file=db_file, schema_file=schema_file)
    print(schema)


if __name__ == "__main__":
    cli()
