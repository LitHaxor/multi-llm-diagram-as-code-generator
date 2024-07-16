from RedisPubSub import RedisPubSubManager
from utils.common import create_system_prompt
from utils.placeholders import uml_examples
from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
import json
from supabase import create_client, Client
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from connection_manager import ConnectionManager
from workers.claude_workers import get_claude_response, model_name as claude_model_name
from workers.gemini_workers import get_prompt_response, model_name as gemini_model_name
from workers.openai_workers import get_openai_response, model_name as openai_model_name
from Caching import RedisCache
RedisPubSubManager.initialize()


models = {
    "gemini": {
        "function": get_prompt_response,
        "name": gemini_model_name
    },
    "claude": {
        "function": get_claude_response,
        "name": claude_model_name
    },
    'openai': {
        'function': get_openai_response,
        'name': openai_model_name
    }
}

RedisPubSubManager.initialize()

app = FastAPI()
manager = ConnectionManager()
caching = RedisCache()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Middleware for handling authentication
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ignore_paths = ["/auth", "/api/login", "/api/register", '/about']
        if request.url.path not in ignore_paths:
            token = request.cookies.get("access_token")
            refresh_token = request.cookies.get("refresh_token")
            if token and refresh_token:
                try:
                    supabase.auth.set_session(access_token=token, refresh_token=refresh_token)
                    request.cookies['user_id'] = supabase.auth.get_user().model_dump().get('user').get('id')
                except Exception as e:
                    # Handle the exception by logging it or any other method you prefer
                    print(f"Failed to set session: {e}")
                    return RedirectResponse(url="/auth")
            else:
                return RedirectResponse(url="/auth")
        response = await call_next(request)
        return response

app.add_middleware(AuthMiddleware)

# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the index.html file"""
    with open("index.html", encoding='utf-8') as f:
        return HTMLResponse(content=f.read(), media_type="text/html")

@app.get("/auth", response_class=HTMLResponse)
async def auth():
    """Serve the auth.html file"""
    with open("auth.html", encoding='utf-8') as f:
        return HTMLResponse(content=f.read(), media_type="text/html")

@app.get("/about")
async def about():
    """Serve the about.html file"""
    with open("about.html", encoding='utf-8') as f:
        return HTMLResponse(content=f.read(), media_type="text/html")

@app.get("/api/user/me")
async def get_user():
    """Get the current user"""
    user = supabase.auth.get_user()
    if user is None:
        return {"status": "error", "message": "User not authenticated"}
    user = user.model_dump()
    return {
        "id": user.get('user').get('id'),
        "email": user.get('user').get('email'),
    }

@app.get("/api/placeholders")
async def get_placeholders(uml_type: str):
    """Get the UML examples for each UML type"""
    return uml_examples[uml_type]

@app.post('/api/login')
async def login(data: dict, response: Response):
    """Login route for users to sign in with email and password"""
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return {"status": "error", "message": "Email and password are required"}
    try:
        result = supabase.auth.sign_in_with_password(credentials={
            "email": email,
            "password": password
        })

        session = result.model_dump().get('session')

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
        print(f"Error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post('/api/register')
async def signup(data: dict, response: Response):
    email = data.get('email')
    password = data.get('password')
    organisation = data.get('organization')
    experience = data.get('experience')
    if not email or not password:
        return {"status": "error", "message": "Email and password are required"}
    try:
        result = supabase.auth.sign_up(credentials={
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "organisation": organisation,
                    "experience": experience
                }
            },
        })
        session = result.model_dump().get('session')

        if session:
            access_token = session.get('access_token')
            refresh_token = session.get('refresh_token')
            response.set_cookie(key="access_token", value=access_token, httponly=True)
            response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
        return result
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get('/api/logout')
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return RedirectResponse(url="/auth")

@app.post('/api/rating')
async def rating(data: dict):
    model_name = data.get('model_name')
    text_data = data.get('text_data')
    rating = data.get('rating')
    uml_type = data.get('uml_type')
    original_prompt = data.get('original_prompt')

    user = supabase.auth.get_user()

    if user is None:
        return {"status": "error", "message": "User not authenticated"}

    user = user.model_dump()
    user_id = user.get('user').get('id')
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
    """Websocket endpoint for handling communication between the client and server"""
    await manager.connect(websocket, client_id)
    RedisPubSubManager.subscribe(client_id)

    async def send_message(channel, message):
        try:
            await manager.send_message(message, client_id)
        except ValueError as e:
            print(f"Initial send_message error: {str(e)}")
            await manager.send_message(f"Error: {str(e)}", client_id)

    asyncio.create_task(RedisPubSubManager.listen(send_message))

    try:
        while True:
            text_data = await websocket.receive_text()
            data = json.loads(text_data)

            uml_type = data["uml_type"]
            original_prompt = data['text']

            prompt = create_system_prompt(original_prompt, uml_type)

            for model in models:
                try:
                    cache_key = f"{models[model]['name']}-{original_prompt}"
                    response_cached = caching.get(cache_key)

                    if response_cached:
                        await manager.send_message(response_cached, client_id)
                    else:
                        task = models[model]["function"].delay(prompt, client_id, uml_type, original_prompt)
                        RedisPubSubManager.redis.set(task.id, client_id)
                except Exception as e:
                    print(f"Error: {str(e)}")

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        RedisPubSubManager.unsubscribe(client_id)
    except Exception as e:
        error_message = json.dumps({"text": f"Error: {str(e)}", "user": "system"})
        await manager.send_message(error_message, client_id)
        RedisPubSubManager.unsubscribe(client_id)
        manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)