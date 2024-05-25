from dotenv import load_dotenv
load_dotenv()
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from connection_manager import ConnectionManager
from workers.claude_workers import get_claude_response
from workers.gemini_workers import get_prompt_response
from workers.openai_workers import get_openai_response
from utils.common import create_system_prompt, santise_markdown_text


models = {
    "gemini": {
        "function": get_prompt_response,
        "name": 'gemini'
    },
    # "claude": {
    #     "function": get_claude_response,
    #     "name": 'claude'
    # },
    # 'openai': {
    #     'function': get_openai_response,
    #     'name': 'openai'
    # }
}

app = FastAPI()
manager = ConnectionManager()

# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html") as f:
        return HTMLResponse(content=f.read(), media_type="text/html")
    
# @app.post("/send")
# async def send_message(message: str):
#     return get_openai_response(message)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            text_data = await websocket.receive_text()
            data = json.loads(text_data)

            uml_type = data["uml_type"]
            text_data = data['text']
            
            text = create_system_prompt(text_data, uml_type)

            for model in models:
                try:
                    task = models[model]["function"].delay(text, websocket, manager)

                    while not task.ready():
                        await asyncio.sleep(1)
                    result = task.result

                    message = {
                        "text": santise_markdown_text(result),
                        "user": models[model]["name"],
                    }

                    manager.send_message(json.dumps(message), websocket)
                except Exception as e:
                    print(f"Error: {str(e)}")
        
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        error_message = json.dumps({"text": f"Error: {str(e)}", "user": "system"})
        await manager.send_message(error_message, websocket)
        manager.disconnect(websocket)
