
import prefect
from yesterdays_hackernews import utils
from yesterdays_hackernews.send import send_mesage

def get_emails_to_send() -> list[str]:
    yesterday = utils.get_yesterday()
    articles_links_and_title = utils.get_yesterdays_top_ten(yesterday)[:14]
    print(f"Got {len(articles_links_and_title )} artciles for {yesterday}")
    ix = utils.hours_since_8am_mt()
    if 0 <= ix < len(articles_links_and_title) - 1 and ix % 2 == 0:
        url1, title1 = articles_links_and_title[ix]
        em1 = utils.get_email_html(url1, title1)
        url2, title2 = articles_links_and_title[ix + 1]
        em2 = utils.get_email_html(url2, title2)
        return [(title1, em1), (title2, em2)]
    else:
        return []


@prefect.task
def pipeline():
    emails = utils.get_emails_to_send()
    for title, html_output in emails:
        # TODO use db to get
        # TODO do I need to track what has been sent to people? probably...
        # for email in os.environ["NEWS_EMAILS"].split():
        send_mesage(email, f"Hacker News: '{title}'", html_output)


if __name__ == "__main__":
    # check 5 minutes past the hour
    schedule = prefect.schedules.CronSchedule(cron="5 * * * *")
    with prefect.Flow("yesterdays_hackernews", schedule=schedule) as flow:
        pipeline()
    flow.run()
