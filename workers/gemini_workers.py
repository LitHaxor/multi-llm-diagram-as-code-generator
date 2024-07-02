import json
import os
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai
from celery import Celery
from RedisPubSub import RedisPubSubManager
from utils.common import santise_markdown_text
from Caching import RedisCache

GEMENI_API_KEY = os.getenv('GOOGLE_AI_API_KEY')

if GEMENI_API_KEY is None:
    raise ValueError("GOOGLE_AI_API_KEY is not set")

genai.configure(api_key= GEMENI_API_KEY)

gemeni_app = Celery(
    'gemeini',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['workers.gemini_workers'], 
    broker_connection_retry_on_startup=True
)

RedisPubSubManager.initialize()
model_name = 'gemini-1.5-flash-latest'

caching = RedisCache()

if __name__ == '__main__':
    gemeni_app.start()

@gemeni_app.task
def get_prompt_response(prompt: str, client_id: str, uml_type: str, original_prompt: str):
    model = genai.GenerativeModel(model_name)
    print(prompt)
    try:
        response = model.generate_content(prompt)
        text = response.text

        result = json.dumps({
            "text": santise_markdown_text(text),
            "user": model_name,
            "uml_type": uml_type,
            "original_prompt": original_prompt,
        })

        RedisPubSubManager.publish(client_id, result)
        cache_key = f"{model_name}-{original_prompt}"
        caching.set(cache_key,result)

        return text
    except AttributeError:
        return "No response text available"
    except Exception as e:
        return f'{type(e).__name__}: {e}'
    