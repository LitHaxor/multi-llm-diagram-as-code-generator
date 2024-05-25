from dotenv import load_dotenv
load_dotenv()
import asyncio
import json
from supabase import create_client, Client
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from connection_manager import ConnectionManager
from workers.claude_workers import get_claude_response
from workers.gemini_workers import get_prompt_response
from workers.openai_workers import get_openai_response
from utils.common import create_system_prompt, santise_markdown_text
from RedisPubSub import RedisPubSubManager
import os

models = {
    "gemini": {
        "function": get_prompt_response,
        "name": 'gemini'
    },
    "claude": {
        "function": get_claude_response,
        "name": 'claude'
    },
    'openai': {
        'function': get_openai_response,
        'name': 'openai'
    }
}

app = FastAPI()
manager = ConnectionManager()
pubsub = RedisPubSubManager()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html") as f:
        return HTMLResponse(content=f.read(), media_type="text/html")
    
@app.post('/api/rating')
async def rating(data: dict):
    model_name = data.get('model_name')
    text_data = data.get('text_data')
    rating = data.get('rating')
    client_id = data.get('client_id')
    uml_type = data.get('uml_type')
    original_prompt = data.get('original_prompt')

    try:
        supabase.table('ratings').insert([{
            'model_name': model_name,
            'text_data': text_data,
            'rating': rating,
            'client_id': client_id,
            'uml_type': uml_type,
            'user_prompt': original_prompt
        }]).execute()

        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    



@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    pubsub.subscribe(client_id)

    async def send_message(message):
        await manager.send_message(message, client_id)
    
    asyncio.create_task(pubsub.listen(send_message))

    try:
        while True:
            text_data = await websocket.receive_text()
            data = json.loads(text_data)

            uml_type = data["uml_type"]
            original_prompt = data['text']
            
            prompt = create_system_prompt(original_prompt, uml_type)

            for model in models:
                try:
                    task = models[model]["function"].delay(prompt, client_id, uml_type, original_prompt)
                    pubsub.redis.set(task.id, client_id)
                except Exception as e:
                    print(f"Error: {str(e)}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        pubsub.unsubscribe(client_id)
    except Exception as e:
        error_message = json.dumps({"text": f"Error: {str(e)}", "user": "system"})
        await manager.send_message(error_message, websocket)
        pubsub.unsubscribe(client_id)
        manager.disconnect(websocket)
