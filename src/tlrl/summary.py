import os
import time
from typing import Optional

import tiktoken
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API"])

GPT_MODEL = "gpt-4o-mini"
ENC = tiktoken.encoding_for_model(GPT_MODEL)
MAX_TOKENS = 8192 * 2
SLACK_TOKENS = 500


def get_num_tokens(text: str) -> int:
    return len(list(ENC.encode(text)))


def get_summary(
    title: str, text: str, retries: int = 3, initial_wait=1
) -> Optional[str]:
    # system_prompt = "You write zippy summaries for an news letter."
    system_prompt = "You are a helpful assistant."
    prompt = f"""
Summarize the following text into a concise two to three sentence blurb to hook potential readers.
Respond with "Unable to summarize" if the text is blocked behind a paywall or procedural (e.g. patch notes) or a generic message such as:
- Notion is a ...

Please adhere to these guidelines:
- Do not reference the "article."
- Do not use passive voice.
- Use short sentences.
- Minimize the use of adjectives.
- Use common words where possible.

Here is the text:

{title}

{text}
"""
    system_tokens = ENC.encode(system_prompt)
    tokens = ENC.encode(prompt)
    tot_tokens = len(tokens) + len(system_tokens)
    if tot_tokens > MAX_TOKENS - SLACK_TOKENS:
        print(
            f"WARN: Truncating tokens from {len(tokens)} -> {MAX_TOKENS - SLACK_TOKENS - len(system_tokens)}"
        )
        prompt = ENC.decode(tokens[: MAX_TOKENS - SLACK_TOKENS - len(system_tokens)])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    for _ in range(retries):
        try:
            response = client.chat.completions.create(
                model=GPT_MODEL, messages=messages, temperature=0.3
            )
        except Exception as e:
            print(f"ERROR: Failed to get summary {e}")
            time.sleep(initial_wait)
            initial_wait = initial_wait * 2
        else:
            summary = response.choices[0].message.content
            if summary.lower().rstrip('."').lstrip('"') == "unable to summarize":
                print("INFO: GPT chose not to summarize")
                return None
            return summary
    print("WARN Failed to get summary")
    return None
