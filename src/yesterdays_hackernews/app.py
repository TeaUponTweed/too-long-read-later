import base64
import datetime
import functools
import os
import pathlib
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

import css_inline
import markdown
import prefect
import pytz
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from lxml.html.clean import Cleaner
from readability import Document

from yesterdays_hackernews.send import send_mesage


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


def get_emails_to_send() -> list[str]:
    yesterday = get_yesterday()
    articles_links_and_title = get_yesterdays_top_ten(yesterday)[:14]
    print(f"Got {len(articles_links_and_title )} artciles for {yesterday}")
    ix = hours_since_8am_mt()
    if 0 <= ix < len(articles_links_and_title) - 1 and ix % 2 == 0:
        url1, title1 = articles_links_and_title[ix]
        em1 = get_email_html(url1, title1)
        url2, title2 = articles_links_and_title[ix + 1]
        em2 = get_email_html(url2, title2)
        return [(title1, em1), (title2, em2)]
    else:
        return []


@prefect.task
def pipeline():
    emails = get_emails_to_send()
    for title, html_output in emails:
        for email in os.environ["NEWS_EMAILS"].split():
            send_mesage(email, f"Hacker News: '{title}'", html_output)


if __name__ == "__main__":
    schedule = prefect.schedules.CronSchedule(cron="5 * * * *")
    with prefect.Flow("yesterdays_hackernews", schedule=schedule) as flow:
        pipeline()
    flow.run()
