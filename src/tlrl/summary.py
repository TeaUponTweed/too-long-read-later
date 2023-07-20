import openai
import os
import tiktoken
import json
import requests
import sys
from fake_useragent import UserAgent
try:
    UA = UserAgent(use_external_data=True)
except:
    UA = UserAgent()

openai.api_key = os.environ['OPENAI_API']
from bs4 import BeautifulSoup


# from tiktoken import Tokenizer
# tokenizer = Tokenizer()
enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
GPT_MODEL = "gpt-4"
MAX_TOKENS = 4096
def get_num_tokens(text):
    return len(list(enc.encode(text)))

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
    prompt = f'''
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
'''
    tokens = enc.encode(prompt)
    if len(tokens) > MAX_TOKENS:
        print(f"WARN: Truncating tokens from {len(tokens)} to {MAX_TOKENS}" )
    prompt = enc.decode(tokens[:MAX_TOKENS])
    messages = [
        # {"role": "system", "content": "Your goal is to summarize content from a webpage. You should produce no more than a few sentences and try to make your summaries pop."},
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Specify the model ID
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message['content']

def main(url):
    headers = {
        "User-Agent": UA['google chrome']
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = ' '.join(t.strip() for t in soup.findAll(text=True) if t.parent.name not in ['style', 'script', 'head', 'title', 'meta', '[document]'])
    summary = get_summary(text)
    return summary


if __name__ == '__main__':
    main(sys.argv[1])
