import json
import os
import sys
from typing import Optional

import openai
import requests
import tiktoken

openai.api_key = os.environ["OPENAI_API"]
from bs4 import BeautifulSoup

GPT_MODEL = "gpt-3.5-turbo"
ENC = tiktoken.encoding_for_model(GPT_MODEL)
MAX_TOKENS = 4096
SLACK_TOKENS = 500


def get_num_tokens(text: str) -> int:
    return len(list(ENC.encode(text)))


def get_summary(
    title: str, text: str, retries: int = 3, initial_wait=1
) -> Optional[str]:
    system_prompt = "You are a helpful assistant."
    prompt = f"""
Craft a two to three sentence blurb about the article, providing pertinent context and intriguing potential readers.
Just provide the summary, do not reference "the article", "in this article", etc.
If the article is inaccessible or procedural, such as a source code listing or release/patch notes, respond with "Unable to summarize".

Follow these rules:
- Use short sentences.
- Avoid the use of adjectives.
- Eliminate every superfluous word.
- Do not use passive tense
- Do not summarize documentation, patch notes, release notes, or source code

Here is the article.
Title: {title}

Text: {text}
"""
    system_tokens = ENC.encode(system_prompt)
    tokens = ENC.encode(prompt)
    if len(tokens) > MAX_TOKENS - SLACK_TOKENS:
        print(
            f"WARN: Truncating tokens from {len(tokens)} -> {MAX_TOKENS-SLACK_TOKENS}"
        )
        prompt = ENC.decode(tokens[: MAX_TOKENS - SLACK_TOKENS])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    for _ in range(retries):
        try:
            response = openai.ChatCompletion.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=0.1,
            )
        except openai.error.ServiceUnavailableError:
            print("INFO waiting and retrying to get summary")
            time.sleep(initial_wait)
            initial_wait = initial_wait * 2
        else:
            summary = response.choices[0].message["content"]
            if summary.lower().rstrip('."').lstrip('"') == "unable to summarize":
                print("INFO GPT chose not to summarize")
                return None
            return summary
    print("WARN Failed to get summary")
    return None


if __name__ == "__main__":
    main(sys.argv[1])
