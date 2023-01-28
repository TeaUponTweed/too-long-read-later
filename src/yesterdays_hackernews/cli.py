import math
import sqlite3
from typing import Optional

import click
import pandas as pd
import requests

from yesterdays_hackernews import db, utils
from yesterdays_hackernews.scraper import ingest_date


@click.group()
def cli():
    pass


@cli.command("cat-link")
@click.argument("link", required=True, type=str)
@click.option("-u", "--user-uuid", required=False, type=str, default=None)
@click.option("--inline/--no-inline", "inline", default=True)
def cat_link(link: str, user_uuid: Optional[str], inline: bool):
    title, html, _ = utils.extract_content(utils.get_page_response(link).text, url=link)
    if inline:
        html = utils.apply_template(
            "email_template.html",
            {
                "article_title": title,
                "article_url": link,
                "article_body": html,
                "user_uuid": user_uuid,
            },
        )
    else:
        html = utils.apply_template(
            "email_template_no_inline.html",
            {
                "article_title": title,
                "article_url": link,
                "user_uuid": user_uuid,
            },
        )
    print(html)


@cli.command("ingest")
@click.option("-d", "--db-file", required=True, type=str)
@click.option("--date", required=True, type=str)
def ingest_hn_date(db_file: str, date: str):
    conn = utils.get_connection(db_file)
    url = "https://news.ycombinator.com/front"
    to_insert_df = ingest_date(url, date)
    with db.transaction(conn):
        db.insert_get_id(conn, "articles", to_insert_df)


def init_db_impl(db_file: str, schema_file: str) -> str:
    conn = utils.get_connection(db_file)
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


@cli.command("test-send")
@click.option("-d", "--db-file", required=True, type=str)
@click.option("-e", "--email", "allowed_email", required=True, type=str)
def test_send(db_file: str, allowed_email: str):
    schema = init_db_impl(db_file=db_file, schema_file=schema_file)
    for email, title, content, article_id, user_id in gen_emails_to_send():
        if email != allowed_email:
            continue
        send_mesage(email, f"Hacker News: '{title}'", content)
        with db.transaction(conn):
            conn.execute(
                "insert into feedback(user_id,article_id) values (?,?)",
                (user_id, article_id),
            )


if __name__ == "__main__":
    cli()
