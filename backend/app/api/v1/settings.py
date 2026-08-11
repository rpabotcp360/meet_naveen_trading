from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.schemas import SettingsUpdate
from app.services.app_state import app_state
from app.storage.database import get_db
from app.storage.repositories import SettingsRepository

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings(session: Session = Depends(get_db)):
    repo = SettingsRepository(session)
    return repo.get_all()


@router.patch("")
async def update_settings(
    payload: SettingsUpdate,
    session: Session = Depends(get_db),
):
    repo = SettingsRepository(session)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    result = repo.update(updates)
    if "universe_source" in updates:
        await app_state.on_watchlist_changed()
    return result
