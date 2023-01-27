Sends the top 10 of yesterdays hackernews stories directly to your inbox.
TODO
- setup scraper to run once per day
- setup sender to send N random emails
	- only to confirmed emails
- allow people to undo feedback
- populate users in database using form

```bash
pip install -r dev-requirements
pip-compile
pip-compile -o requirements_extras.txt --extra python-readability
```
