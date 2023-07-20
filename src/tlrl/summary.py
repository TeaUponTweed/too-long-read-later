import json
import os
import sys

import openai
import requests
import tiktoken

openai.api_key = os.environ["OPENAI_API"]
from bs4 import BeautifulSoup

# from tiktoken import Tokenizer
# tokenizer = Tokenizer()
GPT_MODEL = "gpt-3.5-turbo"
ENC = tiktoken.encoding_for_model(GPT_MODEL)
MAX_TOKENS = 4096


def get_num_tokens(text):
    return len(list(ENC.encode(text)))


def get_summary(text):
    # Initialize the messages array
    system_prompt = "You are a helpful assistant."
    #     prompt = f'''
    # Please write a one or two sentence blurb about the article. Your goal is to provide some context for the article and hook a potential reader.
    # Ignore any details not related to the article content such as front matter, author bios, etc.
    # If the request is blocked or almost empty, just respond "Can not summarize". Here is the article: {text}
    # '''
    #     prompt = f'''
    # Compose a succinct, one to two sentence synopsis of the article that offers an engaging preview of its content to potential readers.
    # Please disregard any non-content-related aspects like front matter or author bios.
    # f the article is inaccessible or lacks substantial content, simply respond with "Unable to summarize". Now, let's proceed to the article:
    # '''
    prompt = f"""
Craft a two to three sentence blurb about the article, providing pertinent context and intriguing potential readers.
Disregard non-content information such as front matter or author bios.
Respond with "Unable to summarize" if the article is inaccessible or scant on content.

Follow these rules:
- Do not reference "The Article", instead just provide the summary
- Use short sentences.
- Avoid the use of adjectives.
- Eliminate every superfluous word.
- Do not use passive tense

Here is the article:

{text}
"""
    system_tokens = ENC.encode(system_prompt)
    tokens = ENC.encode(prompt)
    if len(tokens) > MAX_TOKENS:
        print(f"WARN: Truncating tokens from {len(tokens)} -> {MAX_TOKENS}")
        prompt = ENC.decode(tokens[:MAX_TOKENS-len(system_tokens)-30])

    messages = [
        # {"role": "system", "content": "Your goal is to summarize content from a webpage. You should produce no more than a few sentences and try to make your summaries pop."},
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    response = openai.ChatCompletion.create(
        model=GPT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message["content"]


if __name__ == "__main__":
    main(sys.argv[1])
