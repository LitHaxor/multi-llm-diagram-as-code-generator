from celery import Celery
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
import os
import json 
from RedisPubSub import RedisPubSubManager
from utils.common import santise_markdown_text
from Caching import RedisCache

OPEN_AI_KEY = os.getenv('OPEN_AI_KEY')

if OPEN_AI_KEY is None:
    raise ValueError("OPEN_AI_KEY is not set")

openai = OpenAI(
    api_key= OPEN_AI_KEY
)

model_name = 'gpt-4o'

openai_worker = Celery(
    'openai_workers',
    broker='redis://localhost:6379/2',
    backend='redis://localhost:6379/2',
    include=['workers.openai_workers'],
    broker_connection_retry_on_startup=True,
)
RedisPubSubManager.initialize()
caching = RedisCache()

@openai_worker.task
def get_openai_response(prompt: str, client_id:str, uml_type:str, original_prompt:str):
    try:
        completion = openai.chat.completions.create(
            model=model_name,
            messages=[
                {'role': 'user', 'content': prompt}
            ]
        )
        response = completion.to_dict()

        text = response['choices'][0]['message']['content']

        result = json.dumps({
            "text": santise_markdown_text(text),
            "user": model_name,
            "uml_type": uml_type,
            "original_prompt": original_prompt,
        })

        RedisPubSubManager.publish(client_id,result)
        cache_key = f"{model_name}-{original_prompt}"
        caching.set(cache_key,result)

        return text
    except Exception as e:
        return str(e)