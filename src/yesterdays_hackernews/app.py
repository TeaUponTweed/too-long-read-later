import base64
import datetime
import functools
import os
import pathlib
from datetime import datetime, timedelta, timezone

import markdown
import prefect
import pytz
import requests
import trafilatura
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from yesterdays_hackernews.send import send_mesage


def hours_since_8am_mt():
    mt = pytz.timezone("US/Mountain")
    now = datetime.now(mt)
    eight_am_today = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour < 8:
        eight_am_today = eight_am_today - datetime.timedelta(days=1)
    hours_passed = (now - eight_am_today).total_seconds() / 3600
    return round(hours_passed)


def get_yesterday() -> str:
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


def get_markdown(url: str) -> str:
    downloaded = trafilatura.fetch_url(url)
    markdown_text = trafilatura.extract(
        downloaded,
        include_images=True,
        include_comments=False,
        include_formatting=True,
        include_links=True,
    )
    return markdown_text


def get_articles_links_and_title(response: requests.Response) -> tuple[str, str]:
    soup = BeautifulSoup(response.text, "html.parser")
    title_lines = soup.find_all("span", class_="titleline")
    links = [line.find("a") for line in title_lines]
    return [(link["href"], link.string) for link in links if link['href'].startswith('http')][:14]


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
    # markdown_text = get_markdown(link)
    # extensions = [
    #     "markdown.extensions.fenced_code",
    #     "markdown.extensions.tables",
    #     "markdown.extensions.sane_lists",
    # ]
    # html_output = markdown.markdown(markdown_text, extensions=extensions)
    html_output = apply_template(
        "email_template.html",
        {"article_title": title, "article_url": link}#, "article_body": html_output},
    )
    return html_output

def get_emails_to_send() -> list[str]:
    yesterday = get_yesterday()
    articles_links_and_title = get_yesterdays_top_ten(yesterday)
    print(f"Got {len(articles_links_and_title )} artciles for {yesterday}")
    ix = hours_since_8am_mt()
    if 0 <= ix < len(articles_links_and_title) - 1 and ix % 2 == 0:
        url1, title1 = articles_links_and_title[ix]
        em1 = get_email_html(url1, title1)
        url2, title2 = articles_links_and_title[ix+1]
        em2 = get_email_html(url2, title2)
        return [(title1,em1), (title2,em2)]
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
