import google.generativeai as genai
from celery import Celery
from ..config import GEMENI_API_KEY

if GEMENI_API_KEY is None:
    raise ValueError("GEMENI_API_KEY is not set")

genai.configure(api_key= GEMENI_API_KEY)

gemeni_app = Celery(
    'gemeini',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['workers.gemeni_workers'], 
    broker_connection_retry_on_startup=True
)


if __name__ == '__main__':
    gemeni_app.start()

@gemeni_app.task
def get_prompt_response(prompt: str):
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print(prompt)
    try:
        response = model.generate_content(prompt)
        text = response.text
        print(text)
        return text
    except AttributeError:
        return "No response text available"
    except Exception as e:
        return f'{type(e).__name__}: {e}'
