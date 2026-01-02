# app/ws/manager.py
from fastapi import WebSocket
from shared.logger import get_logger

logger = get_logger("WSConnectionManager")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        to_remove = []
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)

            except Exception as e:
                logger.exception(f"Unexpected WebSocket error: {e}")
                to_remove.append(ws)

        for ws in to_remove:
            self.disconnect(ws)