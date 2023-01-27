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


def get_page_response(url: str) -> requests.Response:
    # parse url to get response
    o = urlparse(url)
    query = parse_qs(o.query)
    # extract the URL without query parameters
    url = o._replace(query=None).geturl()
    response = requests.get(url, params=query)
    return response


def extract_content(html: str, url: str) -> Tuple[str, str, List[float]]:
    html = convert_to_absolute_links(url=url, html=html)
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


# @functools.lru_cache(maxsize=1)
# def get_yesterdays_top_ten(yesterday) -> list[tuple[str, str]]:
#     url = "https://news.ycombinator.com/front"
#     response = requests.get(url, params={"day": yesterday})
#     links_and_title = get_articles_links_and_title(response)
#     return links_and_title


def apply_template(template_name: str, context: dict) -> str:
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_name)
    return template.render(context)


# def get_email_html(link, title):
#     _, html_output = extract_link(link)
#     html_output = apply_template(
#         "email_template.html",
#         {"article_title": title, "article_url": link, "article_body": html_output},
#     )
#     return html_output


@functools.cache
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
                "SELECT email, user_uuid, rowid FROM users WHERE user_uuid = ?",
                (user_uuid,),
            ).fetchone()
        if len(ret):
            (email, user_uuid, row_id) = ret
            return UserInfo(email=email, user_uuid=user_uuid, row_id=row_id)

    if row_id is not None:
        with db.transaction(conn):
            ret = conn.execute(
                "SELECT email, user_uuid, rowid FROM users WHERE rowid = ?", (row_id,)
            ).fetchone()
        if len(ret):
            (email, user_uuid, row_id) = ret
            return UserInfo(email=email, user_uuid=user_uuid, row_id=row_id)

    if email is not None:
        with db.transaction(conn):
            ret = conn.execute(
                "SELECT email, user_uuid, rowid FROM users WHERE email = ?", (email,)
            ).fetchone()
        if len(ret):
            (email, user_uuid, row_id) = ret
            return UserInfo(email=email, user_uuid=user_uuid, row_id=row_id)
    return None


def get_articles_without_feedback(
    conn: sqlite3.Connection, date: str, user_row_ids: Optional[List[int]] = None
) -> List[Tuple[int, int]]:
    q = """
    select articles.rowid as article_id, users.rowid as user_uuid
    from articles
    cross join users
    where article_hn_date = ?
    and not exists (
        select * from feedback
        where articles.rowid = feedback.article_id
        and users.rowid = feedback.user_id
    )
    """
    with db.transaction(conn):
        if user_row_ids is not None:
            q = q + " and users.rowid in ?"
            ret = conn.execute(q, (date, tuple(user_row_ids))).fetchall()
        else:
            ret = conn.execute(q, (date,)).fetchall()
    return list(ret)


MT = timezone(timedelta(hours=-7))  # Mountain Time is -7 hours from UTC


def get_yesterday_mt():
    yesterday = datetime.now(MT) - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")
