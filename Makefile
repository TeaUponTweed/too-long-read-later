.PHONY: install
install:
	uv sync
	uv pip install -e .

.PHONY: polish
polish:
	uv run isort src tests
	uv run black src tests

.PHONY: check-env
check-env: check-email-env check-scraper-env

.PHONY: check-email-env
check-env:
ifndef SMTP_UN
	$(error SMTP_UN is undefined)
endif
ifndef SMTP_PW
	$(error SMTP_PW is undefined)
endif
ifndef EMAIL_ADDRESS
	$(error EMAIL_ADDRESS is undefined)
endif
ifndef REAL_TEST_EMAIL_ADDRESS
	$(error REAL_TEST_EMAIL_ADDRESS is undefined)
endif


.PHONY: check-scraper-env
check-scraper-env:
ifndef OPENAI_API
	$(error OPENAI_API is undefined)
endif
ifndef DB_FILE_LOC
	$(error DB_FILE_LOC is undefined)
endif

.PHONY: test
test:
	uv run pytest --cov-report=xml -m "not slow" tests

.PHONY: integration-test
integration-test: check-env
	# clear out db
	rm -f $(DB_FILE_LOC)
	# initialize a new db
	sqlite3 $(DB_FILE_LOC) < ./schema.sql
	# ingest a few articles
	python -c 'from tlrl.scraper import pipeline; pipeline.run(3)'
	# insert a few users
	sqlite3 $(DB_FILE_LOC) "INSERT OR IGNORE INTO users (user_uuid, email, confirmed, num_articles_per_day) VALUES \
		('some-uuid-1', 'test@gmail.com', 0, 30), \
		('some-uuid-2', '$(REAL_TEST_EMAIL_ADDRESS)', 1, 30);"
	# run send
	python -c 'from tlrl.sender import pipeline; pipeline.run(force_run_now=True)'


.PHONY: docker
docker:
	docker build -t news-scraper:latest -f containers/Dockerfile_scraper .
	docker build -t news-sender:latest  -f containers/Dockerfile_sender  .
	docker build -t news-server:latest  -f containers/Dockerfile_server  .

DB_DIR := $(dir $(DB_FILE_LOC))
DB_FILE_NAME := $(notdir $(DB_FILE_LOC))
.PHONY: docker-scrape
docker-scrape: check-scraper-env
	docker run \
		-v $(DB_DIR):/opt/db \
		-e DB_FILE_LOC="/opt/db/$(DB_FILE_NAME)" \
		-e OPENAI_API=$$OPENAI_API \
		--entrypoint "/bin/sh" \
		server_config-yesterdays_news_scraper:latest -c "uv run python -c 'from tlrl.scraper import pipeline; pipeline.run()'"
