Sends the top 10 of yesterdays hackernews stories directly to your inbox.
TODO
- setup sender to send N random emails
	- only to confirmed emails
- allow people to undo feedback
- populate users in database using form
- get score as a feature

```bash
pip install -r dev-requirements
pip-compile
pip-compile -o requirements_extras.txt --extra python-readability
```

```sql
with send_count as (
select user_id,count(*) as num_sent
from feedback
join articles on articles.rowid = feedback.article_id
where articles.article_hn_date = ?
group by user_id
)
select email from users where confirmed and num_articles
left join send_count on users.rowid = send_count.user_id
where send_count.num_sent < users.num_articles_per_day
```

```sql
    with send_count as (
        select user_id,count(*) as num_sent
        from feedback
        join articles on feedback.article_id = articles.rowid
        where articles.date = ?
        group by user_id
    ), active_users as (
        select users.rowid as user_id, users.email from users
        left join send_count on send_count.user_id = users.rowid
        where send_count.num_sent < num_articles_per_day
        and users.confirmed
    )
    select articles.rowid as article_id, users.rowid as user_uuid
    from articles
    cross join active_users
    where article_hn_date = ?
    and not exists (
        select * from feedback
        where articles.rowid = feedback.article_id
        and active_users.rowid = feedback.user_id
    )
```