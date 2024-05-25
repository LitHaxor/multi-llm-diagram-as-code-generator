from celery import Celery
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
import os
import json 
from RedisPubSub import RedisPubSubManager
from utils.common import santise_markdown_text

OPEN_AI_KEY = os.getenv('OPEN_AI_KEY')

if OPEN_AI_KEY is None:
    raise ValueError("OPEN_AI_KEY is not set")

openai = OpenAI(
    api_key= OPEN_AI_KEY
)

openai_worker = Celery(
    'openai_workers',
    broker='redis://localhost:6379/2',
    backend='redis://localhost:6379/2',
    include=['workers.openai_workers'],
    broker_connection_retry_on_startup=True,
)

pubsub = RedisPubSubManager()

@openai_worker.task
def get_openai_response(prompt: str, client_id:str):
    try:
        completion = openai.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'user', 'content': prompt}
            ]
        )
        response = completion.to_dict()
        text = response['choices'][0]['message']['content']

        pubsub.publish(client_id, json.dumps({
            "text": santise_markdown_text(text),
            "user": "openai"
        }))
        
        return text
    except Exception as e:
        return str(e)