import google.generativeai as genai
from celery import Celery
import redis
from dotenv import load_dotenv
load_dotenv()
import os

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

redis_client = redis.Redis(host='localhost', port=6379, db=0)



if __name__ == '__main__':
    gemeni_app.start()

@gemeni_app.task
def get_prompt_response(prompt: str):
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print(prompt)
    try:
        response = model.generate_content(prompt)
        text = response.text
        return text
    except AttributeError:
        return "No response text available"
    except Exception as e:
        return f'{type(e).__name__}: {e}'
