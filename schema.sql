CREATE TABLE IF NOT EXISTS users (
	user_id TEXT NOT NULL,
	email TEXT NOT NULL,
	confirmed INT NOT NULL,
	num_articles_per_day INT NOT NULL,
	UNIQUE(email)
);


CREATE TABLE IF NOT EXISTS articles (
	scrape_date TEXT NOT NULL,
	title TEXT,
	url TEXT NOT NULL,
	-- extracted text
	content TEXT,
	-- features
	readability_rms REAL,
	readability_sum REAL,
	readability_mean REAL,
	num_chars INT,
	num_paragraphs INT,

	UNIQUE(scrape_date, url)
);

-- CREATE TABLE IF NOT EXISTS article_features (
-- 	article_id INT NOT NULL,
-- 	readability_rms REAL,
-- 	readability_sum REAL,
-- 	readability_mean REAL,
-- 	num_words INT,
-- 	FOREIGN KEY(article_id) REFERENCES articles(rowid)
-- );


CREATE TABLE IF NOT EXISTS feedback (
	article_id INT NOT NULL,
	user_id INT NOT NULL,
	sentiment INT,
	format_quality INT,
	should_format INT,
	FOREIGN KEY(article_id) REFERENCES articles(rowid),
	FOREIGN KEY(user_id) REFERENCES users(rowid),
	UNIQUE(article_id, user_id)
);
