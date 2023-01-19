import sys

from yesterdays_hackernews.app import apply_template, extract_link


def scrape(link: str):
    title, html = extract_link(link)
    html = apply_template(
        "email_template.html",
        {"article_title": title, "article_url": link, "article_body": html},
    )
    print(html)


if __name__ == "__main__":
    scrape(sys.argv[1])
