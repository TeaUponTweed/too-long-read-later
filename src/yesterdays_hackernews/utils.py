import base64
import datetime
import functools
import os
import pathlib
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

import css_inline
import markdown
import pytz
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from lxml.html.clean import Cleaner
from readability import Document

from yesterdays_hackernews import db


def convert_to_absolute_links(url: str, html: str) -> str:
    # Download the webpage
    soup = BeautifulSoup(html, "html.parser")

    # Convert all relative links to absolute links
    for link in soup.find_all("a"):
        href = link.get("href")
        if href:
            link["href"] = urljoin(url, href)

    for link in soup.find_all("link", attrs={"rel": "stylesheet"}):
        href = link.get("href")
        if href:
            link["href"] = urljoin(url, href)

    # Return the modified HTML
    return str(soup)


def hours_since_8am_mt():
    mt = pytz.timezone("US/Mountain")
    now = datetime.now(mt)
    eight_am_today = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour < 8:
        eight_am_today = eight_am_today - timedelta(days=1)
    hours_passed = (now - eight_am_today).total_seconds() / 3600
    return round(hours_passed)


def get_yesterday() -> str:
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


_HTML_CLEANER = Cleaner(
    scripts=True,
    javascript=True,
    comments=True,
    style=False,
    inline_style=False,
    links=True,
    meta=False,
    add_nofollow=False,
    page_structure=False,
    processing_instructions=True,
    embedded=False,
    frames=False,
    forms=False,
    annoying_tags=False,
    remove_tags=None,
    remove_unknown_tags=False,
    safe_attrs_only=False,
)


def extract_link(url: str) -> Tuple[str, str, List[float]]:
    # parse url to get response
    o = urlparse(url)
    query = parse_qs(o.query)
    # extract the URL without query parameters
    url = o._replace(query=None).geturl()
    response = requests.get(url, params=query)
    html = convert_to_absolute_links(url=url, html=response.text)
    # inline CSS
    html = css_inline.inline(html)
    doc = Document(html, cleaner=_HTML_CLEANER)
    # extract content
    return (
        doc.title(),
        doc.summary(html_partial=True),
        [el["content_score"] for el in doc.score_paragraphs().values()],
    )


def get_articles_links_and_title(response: requests.Response) -> tuple[str, str]:
    soup = BeautifulSoup(response.text, "html.parser")
    title_lines = soup.find_all("span", class_="titleline")
    links = [line.find("a") for line in title_lines]
    return [
        (link["href"], link.string) for link in links if link["href"].startswith("http")
    ]


@functools.lru_cache(maxsize=1)
def get_yesterdays_top_ten(yesterday) -> list[tuple[str, str]]:
    url = "https://news.ycombinator.com/front"
    response = requests.get(url, params={"day": yesterday})
    links_and_title = get_articles_links_and_title(response)
    return links_and_title


def apply_template(template_name: str, context: dict) -> str:
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_name)
    return template.render(context)


def get_email_html(link, title):
    _, html_output = extract_link(link)
    html_output = apply_template(
        "email_template.html",
        {"article_title": title, "article_url": link, "article_body": html_output},
    )
    return html_output


@functools.cache
def get_connection(db_file: Optional[str] = None) -> sqlite3.Connection:
    if db_file is None:
        db_file = os.environ["DB_FILE_LOC"]
    return sqlite3.connect(db_file, isolation_level=None)


def set_feedback(
    conn: sqlite3.Connection,
    colname: str,
    article_id: int,
    user_id: str,
    sentiment: int,
):
    with db.transaction(conn):
        conn.execute(
            "UPDATE feedback SET ?=? WHERE article_id=? AND user_id=?",
            (colname, sentiment, article_id, user_id),
        )


def confirm(conn: sqlite3.Connection, email: str):
    with db.transaction(conn):
        conn.execute(
            """UPDATE users SET confirmed=? WHERE email=?""",
            (1, email),
        )


def unsubscribe(conn: sqlite3.Connection, user_id: str):
    with db.transaction(conn):
        conn.execute(
            "UPDATE users SET num_articles_per_day=? WHERE user_id=?", (0, user_id)
        )


def subscribe(
    conn: sqlite3.Connection, email: str, user_id: str, num_articles_per_day: int
):
    with db.transaction(conn):
        conn.execute(
            """INSERT INTO users(email,user_id,num_articles_per_day, confirmed) VALUES(?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET num_articles_per_day=?;""",
            (email, user_id, num_articles_per_day, 0, num_articles_per_day),
        )


def get_email(conn: sqlite3.Connection, user_id: str) -> Optional[str]:
    with db.transaction(conn):
        ret = conn.execute(
            "SELCT email from users where user_id = ?", user_id
        ).fetchone()
    if len(ret):
        return ret[0]
    else:
        return None


def get_user_id(conn: sqlite3.Connection, email: str) -> Optional[str]:
    with db.transaction(conn):
        ret = conn.execute("SELCT user_id from users where email = ?", email).fetchone()
    if len(ret):
        return ret[0]
    else:
        return None
