import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("app")


class BrowserWebSocketManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self.state = "offline"

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.append(websocket)
        self.state = "live"

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.connections:
            self.connections.remove(websocket)
        if not self.connections:
            self.state = "offline"

    async def broadcast(self, event_type: str, payload: Any) -> None:
        message = json.dumps({"type": event_type, "data": payload}, default=str)
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_snapshot(self, websocket: WebSocket, snapshot: dict) -> None:
        await websocket.send_text(
            json.dumps({"type": "snapshot", "data": snapshot}, default=str)
        )
