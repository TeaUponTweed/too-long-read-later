# Overview
Sends the top 10 of yesterdays hackernews stories directly to your inbox.
This involves extracting the "content" from the posts and translating them into email.
Users and articles are stored in a sqlite database. See schema.sql for details.
The system is currently running at news.derivativeworks.co and configured to send up to one email per hour between 9AM MT and 8PM MT.

# Installation
```bash
# install dependencies
pip install -r requirements.txt
pip install -e .
# install dev dependencies
pip install -r dev-requirements
# if dependencies change, update requirements.txt
pip-compile
```

# Running
This assumes you will setup 3 services:
- scraper, runs once a day and gets hackewnews articles from previous day
- send, runs hourly and sends emails to subscribers
- server, hosts signup page and provides a REST api for feedback, subscriptions, etc.

To send emails, you need to set `EMAIL_ADDRESS` to a valid gmail you control and `GMAIL_SMTP_PW` to the appropriate string.
See [this post](https://kinsta.com/blog/gmail-smtp-server/) for information.

Finally, you need to set `DB_FILE_LOC` to a location with an already initialized sqlite database.
You can run
```bash
$ python src/tlrl/cli.py init -d path/to/news.db -s schema.sql
```
To initialize the database

# Roadmap
Eventually I would like use these scraping utilities into a chrome extension, similar to pocket but using email, which I actually check.

TODO
- allow people to undo feedback
- open email -> db
- click link -> db
- better feedback ux (currently opens a new tab with no content)
- "should inline" model (a threshold on readability RMS seems good)
- more configurable article times
- improve landing page to make it look nicer and link to extension once it's published
- update extension publish version to 1.1
	- make icon easier to see
	- provide feedback that the email was sent successfully or if not (alert for both is fine)
- use hacker news api rather than scraping https://github.com/HackerNews/API
- look at link filetype to make sure images are scraped correctly


```
docker ps | grep server_config-yesterdays_news_scraper
docker exec -it $CONTAINER_ID /bin/bash
python3 -c 'from tlrl.scraper import pipeline; pipeline.run()'

docker ps | grep server_config-yesterdays_news_sender
docker exec -it $CONTAINER_ID /bin/bash
python3 -c 'from tlrl.scraper import pipeline; pipeline.run()'
```


```
sqlite3 ../databases/news/news.db "select article_hn_date,count(*) from articles group by article_hn_date;"
sqlite3 ../databases/news/news.db "
            with send_count as (
                select user_id,count(*) as num_sent
                from feedback
                join articles on articles.rowid = feedback.article_id
                where articles.article_hn_date = '2023-06-17'
                group by user_id
            )
            select users.rowid,users.email from users
            left join send_count on users.rowid = send_count.user_id
            where users.confirmed and ((send_count.num_sent < users.num_articles_per_day) or send_count.num_sent is null)"
sqlite3 ../databases/news/news.db "
            with send_count as (
                select user_id,count(*) as num_sent
                from feedback
                join articles on articles.rowid = feedback.article_id
                where articles.article_hn_date = '2023-06-17'
                group by user_id
            )
            select users.email,num_sent,num_articles_per_day from users
            left join send_count on users.rowid = send_count.user_id"
```