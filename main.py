from dotenv import load_dotenv
load_dotenv()
import asyncio
import json
from supabase import create_client, Client
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
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

# Middleware for handling authentication
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ignore_paths = ["/auth", "/api/login", "/api/register"]
        if request.url.path not in ignore_paths:
            token = request.cookies.get("access_token")
            refresh_token = request.cookies.get("refresh_token")
            if token and refresh_token:
                supabase.auth.set_session(access_token=token, refresh_token=refresh_token)
            else:
                return RedirectResponse(url="/auth")
        response = await call_next(request)
        return response


app.add_middleware(AuthMiddleware)
# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # This part is simplified assuming authentication middleware is handling user authentication
    with open("index.html") as f:
        return HTMLResponse(content=f.read(), media_type="text/html")
    
@app.get("/auth", response_class=HTMLResponse)
async def auth(request: Request):
    with open("auth.html") as f:
        return HTMLResponse(content=f.read(), media_type="text/html")

@app.post('/api/login')
async def login(data: dict, response: Response):
    email = data.get('email')
    password = data.get('password')
    try:
        result = supabase.auth.sign_in_with_password(credentials={
            "email": email,
            "password": password
        })
        
        session = result.model_dump().get('session')
        print(session)
        if session:
            access_token = session.get('access_token')
            refresh_token = session.get('refresh_token')
            print({
                "access_token": access_token,
                "refresh_token": refresh_token
            })
            response.set_cookie(key="access_token", value=access_token, httponly=True)
            response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
            
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post('/api/register')
async def signup(data: dict, response: Response):
    email = data.get('email')
    password = data.get('password')
    organization = data.get('organization')
    experience = data.get('experience')
    try:
        result = supabase.auth.sign_up(credentials= {
            "email": email,
            "password": password,
        })
        user = result['user']
        user_id = user['id']
        supabase.table('user_experience').insert([
            {
                'user_id': user_id,
                'organization': organization,
                'experience': experience
            }
        ]).execute()
        session = result.get('session')
        if session:
            access_token = session.get('access_token')
            refresh_token = session.get('refresh_token')
            response.set_cookie(key="access_token", value=access_token, httponly=True)
            response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
    

@app.get('/api/logout')
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return RedirectResponse(url="/auth")


@app.post('/api/rating')
async def rating(data: dict, request: Request):
    model_name = data.get('model_name')
    text_data = data.get('text_data')
    rating = data.get('rating')
    uml_type = data.get('uml_type')
    original_prompt = data.get('original_prompt')

    user = supabase.auth.get_user()

    if user is None:
        return {"status": "error", "message": "User not authenticated"}
    
    user_id = user['id']
    try:
        supabase.table('ratings').insert([{
            'model_name': model_name,
            'text_data': text_data,
            'rating': rating,
            'user_id': user_id,
            'uml_type': uml_type,
            'user_prompt': original_prompt
        }]).execute()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def get_current_user_token(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token

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