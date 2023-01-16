import base64
import datetime
import functools
import os
import pathlib

import markdown

# import premailer
import pynliner
import requests
import trafilatura
from bs4 import BeautifulSoup

from yesterdays_hackernews.send import send_mesage

def get_yesterday() -> str:
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


# CSS_FILE = str(
#     (
#         pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
#         / ".."
#         / ".."
#         / "styles"
#         / "modest.css"
#     ).resolve()
# )


def get_markdown(url: str) -> str:
    # response = requests.get(url)
    # soup = BeautifulSoup(response.text, "html.parser")

    # Extract the text
    # text = soup.get_text()

    # Convert the text to markdown
    # markdown_text = markdown.markdown(text)
    downloaded = trafilatura.fetch_url(url)
    markdown_text = trafilatura.extract(
        downloaded,
        include_images=True,
        include_comments=False,
        include_formatting=True,
        include_links=True,
    )
    # # Extract and base64 encode the images
    # img_tags = soup.find_all("img")
    # for img in img_tags:
    #     img_url = img["src"]
    #     img_data = requests.get(img_url).content
    #     base64_img = base64.b64encode(img_data).decode()
    #     img_tag = f'<img src="data:image/jpeg;base64,{base64_img}">'
    #     markdown_text = markdown_text.replace(str(img), img_tag)

    return markdown_text


def get_articles_links_and_title(response: requests.Response) -> tuple[str, str]:
    soup = BeautifulSoup(response.text, "html.parser")
    title_lines = soup.find_all("span", class_="titleline")[:10]
    links = [line.find("a") for line in title_lines]
    return [(link["href"], link.string) for link in links]


def hours_since_8AM():
    now = datetime.datetime.now()
    eight_am_today = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour < 8:
        eight_am_today = eight_am_today - datetime.timedelta(days=1)
    hours_passed = (now - eight_am_today).total_seconds() / 3600
    return round(hours_passed)


@functools.lru_cache(maxsize=1)
def get_yesterdays_top_ten(yesterday) -> list[tuple[str, str]]:
    url = "https://news.ycombinator.com/front"
    response = requests.get(url, params={"day": yesterday})
    links_and_title = get_articles_links_and_title(response)
    assert len(links_and_title) == 10
    return links_and_title


def inline_css(html_string: str, css_string: str) -> str:
    return


from jinja2 import Environment, FileSystemLoader


def apply_template(template_name: str, context: dict) -> str:
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_name)
    return template.render(context)


def pipeline():
    yesterday = get_yesterday()
    articles_links_and_title = get_yesterdays_top_ten(yesterday)
    ix = hours_since_8AM()
    if 0 <= ix < 10:
        link, title = articles_links_and_title[ix]
        markdown_text = get_markdown(link)
        extensions = [
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.sane_lists",
        ]
        html_output = markdown.markdown(markdown_text, extensions=extensions)
        # with open(CSS_FILE, "r") as css:
        #     css_string = css.read()
        # import pdb; pdb.set_trace()
        # print(html_output)
        # html_output = pynliner.Pynliner().from_string(html_output).with_cssString(css_string).run()
        # print(html_output)
        html_output = apply_template(
            "email_template.html",
            {"article_title": title, "article_url": link, "article_body": html_output},
        )
        print(html_output, file=open("test.html", "w"))
        send_mesage("teaupontweed@gmail.com", f"Hacker News: '{title}'", html_output)


if __name__ == '__main__':
    pipeline()
