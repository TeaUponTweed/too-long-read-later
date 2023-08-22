import base64
import datetime
import functools
import os
import pathlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

import pytz
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from jinja2 import Environment, FileSystemLoader
from lxml.html.clean import Cleaner
from readability import Document

from tlrl import db
from tlrl.summary import get_summary


@functools.cache
def get_user_agent() -> UserAgent:
    try:
        return UserAgent(use_external_data=True)
    except:
        return UserAgent()


def convert_to_absolute_links(url: str, html: str) -> str:
    # Download the webpage
    soup = BeautifulSoup(html, "html.parser")
    # TODO get all image blocks and convert source
    # TODO double check CSS stuff
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


def hours_since_5am_mt():
    mt = pytz.timezone("US/Mountain")
    now = datetime.now(mt)
    eight_am_today = now.replace(hour=5, minute=0, second=0, microsecond=0)
    if now.hour < 5:
        eight_am_today = eight_am_today - timedelta(days=1)
    hours_passed = (now - eight_am_today).total_seconds() / 3600
    return round(hours_passed)


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


def get_scores(html: str) -> list[float]:
    doc = Document(html, cleaner=_HTML_CLEANER)
    return [el["content_score"] for el in doc.score_paragraphs().values()]


def get_page_response(
    url: str, timeout: float = 10, max_size: int = 2 * 1024 * 1024
) -> requests.Response:
    # parse url to get response
    o = urlparse(url)
    query = parse_qs(o.query)
    # get fake user agent
    headers = {"User-Agent": get_user_agent()["google chrome"]}
    # extract the URL without query parameters
    url = o._replace(query=None).geturl()
    response = requests.get(
        url, params=query, timeout=timeout, stream=True, headers=headers
    )
    size = 0
    content = bytes()
    for chunk in response.iter_content(chunk_size=1024):
        content += chunk
        size += len(chunk)
        if size > max_size:
            raise ValueError("Response too large, stopping download...")
    # we create a new response with the content that we've downloaded so far
    new_response = requests.Response()
    new_response.status_code = response.status_code
    new_response.headers = response.headers
    new_response._content = content
    return new_response


def extract_content(html: str) -> Tuple[str, str, str]:
    doc = Document(html, cleaner=_HTML_CLEANER)
    text = doc.summary()
    # print(text)
    soup = BeautifulSoup(text, "html.parser")
    text = " ".join(
        t.strip()
        for t in soup.findAll(text=True)
        if t.parent.name
        not in ["style", "script", "head", "title", "meta", "[document]"]
    )
    title = doc.title()
    summary = get_summary(title, text)
    return (title, text, summary)


def get_article_info(response: requests.Response) -> list[tuple[str, str, int]]:
    soup = BeautifulSoup(response.text, "html.parser")
    title_lines = soup.find_all("span", class_="titleline")
    links = [line.find("a") for line in title_lines]
    scores = []
    # get scores
    for subtext in soup.find_all("td", class_="subtext"):
        score = subtext.find("span", class_="score").text.strip().replace(" points", "")
        scores.append(int(score))

    if len(scores) != len(links):
        print("WARN: scraped scores did not align with articles")
        scores = [None for _ in range(len(links))]

    return [
        (link["href"], link.string, score)
        for score, link in zip(scores, links)
        if link["href"].startswith("http")
    ]


def apply_template(template_name: str, context: dict) -> str:
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_name)
    return template.render(context)


def get_connection(db_file: Optional[str] = None) -> sqlite3.Connection:
    if db_file is None:
        db_file = os.environ["DB_FILE_LOC"]
    return sqlite3.connect(db_file, isolation_level=None)


def set_feedback(
    conn: sqlite3.Connection,
    col_name: str,
    article_id: int,
    user_id: int,
    sentiment: int,
):
    if col_name not in ("sentiment", "format_quality", "should_format"):
        raise ValueError(f"Bad feedback column name {col_name}")

    with db.transaction(conn):
        conn.execute(
            f"""
            INSERT INTO feedback(article_id,user_id,{col_name}) VALUES(?,?,?)
            ON CONFLICT (article_id,user_id) DO UPDATE SET {col_name}=excluded.{col_name}
            """,
            (article_id, user_id, sentiment),
        )


def confirm(conn: sqlite3.Connection, email: str):
    with db.transaction(conn):
        conn.execute(
            """UPDATE users SET confirmed=? WHERE email=?""",
            (1, email),
        )


def unsubscribe(conn: sqlite3.Connection, user_uuid: str):
    with db.transaction(conn):
        conn.execute(
            "UPDATE users SET num_articles_per_day=? WHERE user_uuid=?", (0, user_uuid)
        )


def subscribe(
    conn: sqlite3.Connection, email: str, user_uuid: str, num_articles_per_day: int
):
    with db.transaction(conn):
        conn.execute(
            """INSERT INTO users(email,user_uuid,num_articles_per_day, confirmed) VALUES(?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET num_articles_per_day=?;""",
            (email, user_uuid, num_articles_per_day, 0, num_articles_per_day),
        )


@dataclass
class UserInfo:
    email: str
    row_id: int
    user_uuid: str
    confirmed: bool


def get_user_info(
    conn: sqlite3.Connection,
    user_uuid: Optional[str] = None,
    row_id: Optional[int] = None,
    email: Optional[str] = None,
) -> Optional[UserInfo]:
    assert any(
        [(user_uuid is not None), (row_id is not None), (email is not None)]
    ), "Need to specify some user info"
    if user_uuid is not None:
        with db.transaction(conn):
            ret = conn.execute(
                "SELECT email, user_uuid, rowid, confirmed FROM users WHERE user_uuid = ?",
                (user_uuid,),
            ).fetchone()
        if ret is not None and len(ret) > 0:
            (email, user_uuid, row_id, confirmed) = ret
            return UserInfo(
                email=email,
                user_uuid=user_uuid,
                row_id=row_id,
                confirmed=bool(confirmed),
            )

    if row_id is not None:
        with db.transaction(conn):
            ret = conn.execute(
                "SELECT email, user_uuid, rowid, confirmed FROM users WHERE rowid = ?",
                (row_id,),
            ).fetchone()
        if ret is not None and len(ret) > 0:
            (email, user_uuid, row_id, confirmed) = ret
            return UserInfo(
                email=email,
                user_uuid=user_uuid,
                row_id=row_id,
                confirmed=bool(confirmed),
            )

    if email is not None:
        with db.transaction(conn):
            ret = conn.execute(
                "SELECT email, user_uuid, rowid, confirmed FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        if ret is not None and len(ret) > 0:
            (email, user_uuid, row_id, confirmed) = ret
            return UserInfo(
                email=email,
                user_uuid=user_uuid,
                row_id=row_id,
                confirmed=bool(confirmed),
            )
    return None


MT = timezone(timedelta(hours=-7))  # Mountain Time is -7 hours from UTC


def get_yesterday_mt():
    yesterday = datetime.now(MT) - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


@dataclass
class Article:
    title: str
    summary: str
    url: str
    article_id: int


def get_articles(conn: sqlite3.Connection, date: str) -> list[Article]:
    with db.transaction(conn):
        article_data = conn.execute(
            """select rowid, title,summary, url from articles
            where article_hn_date = ?
            and summary is not null
            """,
            (date,),
        ).fetchall()

    articles = [
        Article(
            title=article_title,
            summary=article_summary,
            url=article_url,
            article_id=article_id,
        )
        for article_id, article_title, article_summary, article_url in article_data
    ]
    return articles


def get_subscribed_users(conn: sqlite3.Connection) -> list[UserInfo]:
    with db.transaction(conn):
        subscribed_users = conn.execute(
            """select users.rowid from users
               where users.confirmed and users.num_articles_per_day > 0"""
        ).fetchall()
    # TODO this is very expensive and should be done in batch
    return [get_user_info(conn=conn, row_id=row_id) for row_id, in subscribed_users]
