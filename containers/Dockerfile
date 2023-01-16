FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir -U pip setuptools wheel

COPY . .

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=.

ENTRYPOINT [ "prefect", "deployment", "build", "src/yesterdays_hackernews/app.py:pipeline", "-n", "etl", "--cron", "\"0 * * * *\"" ]
