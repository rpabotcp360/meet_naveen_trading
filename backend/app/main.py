from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.auth import get_valid_session
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.services.app_state import app_state
from app.storage.database import session_scope


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await app_state.startup()
    yield
    await app_state.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/health")
    async def root_health():
        from app.core.timezone import now_utc
        return {"status": "ok", "timestamp": now_utc(), "app": settings.app_name}

    @app.websocket("/ws/live")
    async def live_websocket(websocket: WebSocket):
        token = websocket.query_params.get("token", "")
        with session_scope() as session:
            valid = bool(token) and get_valid_session(session, token) is not None
        if not valid:
            await websocket.close(code=4401)
            return
        await app_state.browser_ws.connect(websocket)
        try:
            await app_state.browser_ws.send_snapshot(
                websocket, app_state.get_snapshot()
            )
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            app_state.browser_ws.disconnect(websocket)

    return app


app = create_app()
