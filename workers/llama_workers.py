import json
from transformers import pipeline
from celery import Celery
from RedisPubSub import RedisPubSubManager
from utils.common import santise_markdown_text
from dotenv import load_dotenv
load_dotenv()
import os

HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')


if HUGGINGFACE_API_KEY is None:
    raise ValueError("HUGGINGFACE_API_KEY is not set")

os.environ['HF_TOKEN'] = HUGGINGFACE_API_KEY
os.environ['HF_HOME'] = '/tmp/huggingface'

pipe = pipeline("text-generation", model="meta-llama/Meta-Llama-3-70B")


llama_app = Celery(
    'llama',
    broker='redis://localhost:6379/3',
    backend='redis://localhost:6379/3',
    include=['workers.llama_workers'],
    broker_connection_retry_on_startup=True,
    

)


RedisPubSubManager.initialize()

if __name__ == '__main__':
    llama_app.start()

@llama_app.task
def get_llama_response(prompt: str, client_id: str, uml_type: str, original_prompt: str):
    try:
        response = pipe(prompt)
        text = response[0]['generated_text']

        RedisPubSubManager.publish(client_id, json.dumps({
            "text": santise_markdown_text(text),
            "user": "llama",
            "uml_type": uml_type,
            "original_prompt": original_prompt,
        }))

        return text
    except Exception as e:
        return str(e)