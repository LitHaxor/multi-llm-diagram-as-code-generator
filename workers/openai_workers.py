from celery import Celery
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
import os

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


@openai_worker.task
def get_openai_response(prompt):
    try:
        print(f"[OpenAI] get_openai_response: {prompt}")
        completion = openai.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'user', 'content': prompt}
            ]
        )
        response = completion.to_dict()
        text = response['choices'][0]['message']['content']
        return text
    except Exception as e:
        return str(e)