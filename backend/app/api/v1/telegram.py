from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.schemas import TelegramConfig
from app.services.app_state import app_state
from app.storage.database import get_db

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/status")
def telegram_status(session: Session = Depends(get_db)):
    return app_state.get_telegram_status(session)


@router.post("/config")
def configure_telegram(
    payload: TelegramConfig,
    session: Session = Depends(get_db),
):
    return app_state.configure_telegram(payload, session)


@router.post("/test")
async def test_telegram(session: Session = Depends(get_db)):
    return await app_state.send_test_telegram(session)
