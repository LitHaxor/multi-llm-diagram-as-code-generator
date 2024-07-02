from anthropic import Anthropic
from celery import Celery
from dotenv import load_dotenv
load_dotenv()
import os
from RedisPubSub import RedisPubSubManager
import json
from utils.common import santise_markdown_text
from Caching import RedisCache


CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

if CLAUDE_API_KEY is None:
    raise ValueError("CLAUDE_API_KEY is not set")

client = Anthropic(
    api_key= CLAUDE_API_KEY
)

claude_app = Celery(
    'claude',
    broker='redis://localhost:6379/1',
    backend='redis://localhost:6379/1',
    include=['workers.claude_workers'], 
    broker_connection_retry_on_startup=True
)

model_name = 'claude-3-sonnet-20240229'

RedisPubSubManager.initialize()
caching = RedisCache()

if __name__ == '__main__':
    claude_app.start()


@claude_app.task
def get_claude_response(prompt: str, client_id: str, uml_type: str, original_prompt: str):
    print(prompt)
    try:
        message = client.messages.create(
            model=model_name,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        text = ""

        for block in message.content:
            text += block.to_dict()['text']

        result = json.dumps({
            "text": santise_markdown_text(text),
            "user": model_name,
            "uml_type": uml_type,
            "original_prompt": original_prompt,
        })
        
        RedisPubSubManager.publish(client_id, result)
        cache_key = f"{model_name}-{original_prompt}"
        caching.set(cache_key, result)

        return text
    except Exception as e:
        print(f"[error] claude_workers.py: get_claude_response: {str(e)}")
        return f'{type(e).__name__}: {e}'




