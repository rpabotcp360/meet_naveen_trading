from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.api.schemas import UpstoxConfig
from app.core.config import get_settings
from app.services.app_state import app_state
from app.storage.database import get_db
from app.storage.repositories import SettingsRepository

router = APIRouter(prefix="/upstox", tags=["upstox"])


@router.get("/status")
def upstox_status(session: Session = Depends(get_db)):
    return app_state.get_upstox_status(session)


@router.post("/config")
def configure_upstox(
    payload: UpstoxConfig,
    session: Session = Depends(get_db),
):
    return app_state.configure_upstox(payload, session)


@router.get("/login-url")
def login_url():
    return {"url": app_state.get_upstox_login_url()}


@router.get("/callback")
async def callback(
    code: str = Query(...),
    session: Session = Depends(get_db),
):
    await app_state.handle_upstox_callback(code, session)
    settings = get_settings()
    return RedirectResponse(
        url=f"http://127.0.0.1:3000/settings?upstox=connected"
    )


@router.post("/disconnect")
def disconnect(session: Session = Depends(get_db)):
    app_state.disconnect_upstox(session)
    return {"ok": True}
