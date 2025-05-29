from typing import Optional

import click

from tlrl import db, utils
from tlrl.scraper import ingest_date
from tlrl.send import send_mesage


@click.group()
def cli():
    pass


@cli.command("cat-link")
@click.argument("link", required=True, type=str)
@click.option("--inline/--no-inline", "inline", default=False)
@click.option("-e", "--email", required=False, type=str, default=None)
def cat_link(link: str, inline: bool, email: Optional[str]):
    inferred_title, text, summary = utils.extract_content(
        utils.get_page_response(link).text
    )

    html = utils.apply_template(
        "email_template.html",
        {
            "articles": [
                utils.Article(
                    title=inferred_title, summary=summary, url=link, article_id=None
                )
            ],
            "user_uuid": None,
        },
    )
    if email is not None:
        send_mesage(email, f"Yesterdays News Now: '{inferred_title}'", html)
    else:
        print(html)
        # print(text)
        # print("-----------")
        # print(summary)


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


if __name__ == "__main__":
    cli()
