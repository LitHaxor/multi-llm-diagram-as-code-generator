from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.task_websockets: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = websocket

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    def store_websocket(self, task_id: str, websocket: WebSocket):
        self.task_websockets[task_id] = websocket

    def get_websocket(self, task_id: str):
        return self.task_websockets.pop(task_id, None)
