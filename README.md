# Overview
Sends the top 10 of yesterdays hackernews stories directly to your inbox.
Uses sqlite as a database. See shema.sql for details.
Currently configured to send up to one email per hour between 9AM MT and 8PM MT.

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
- scraper, runs once a day and gets hackew news articles from previous day
- send, runs hourly and sends emails to subscribers
- server, hosts signup page and provides a REST api for feedback, subscriptions, etc.

To send emails, you need to set `EMAIL_ADDRESS` to a valid gmail you control and `GMAIL_SMTP_PW` to the appropriate string.
See [this post](https://kinsta.com/blog/gmail-smtp-server/) for information.

Finally, you need to set `DB_FILE_LOC` to a location with an already initialized sqlite database.
You can run
```bash
$ python src/yesterdays_hackernews/cli.py init -d path/to/news.db -s schema.sql
```
To initialize the database

# Roadmap

TODO
- allow people to undo feedback
- get hn score as a feature
- open email -> db
- click link -> db
- better feedback ux (currently opens a new tab with no content)
- "should inline" model
- develop a chrome extension
- more configurable article times

