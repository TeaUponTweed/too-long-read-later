.PHONY: install
install:
	pip install --upgrade pip
	pip install -r dev-requirements.txt
	pip install -r requirements.txt -e .

.PHONY: polish
polish:
	isort src tests
	black src tests

.PHONY: check-env
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
ifndef OPENAI_API
	$(error OPENAI_API is undefined)
endif
ifndef DB_FILE_LOC
	$(error DB_FILE_LOC is undefined)
endif
ifndef REAL_TEST_EMAIL_ADDRESS
	$(error REAL_TEST_EMAIL_ADDRESS is undefined)
endif

.PHONY: test
test:
	pytest -m "not slow" tests

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
