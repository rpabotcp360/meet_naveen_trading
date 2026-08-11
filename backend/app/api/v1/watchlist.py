from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.schemas import WatchlistCreate, WatchlistUpdate
from app.services.app_state import app_state
from app.storage.database import get_db
from app.storage.models import WatchlistItem
from app.storage.repositories import WatchlistRepository

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("")
def list_watchlist(segment_id: int | None = None, session: Session = Depends(get_db)):
    repo = WatchlistRepository(session)
    return repo.list_all(segment_id)


@router.post("")
async def add_watchlist(
    payload: WatchlistCreate,
    session: Session = Depends(get_db),
):
    repo = WatchlistRepository(session)
    if repo.get_by_key(payload.instrument_key):
        raise HTTPException(status_code=409, detail="Already in watchlist")
    item = WatchlistItem(**payload.model_dump())
    created = repo.create(item)
    await app_state.on_watchlist_changed()
    return created


@router.patch("/{item_id}")
async def update_watchlist(
    item_id: int,
    payload: WatchlistUpdate,
    session: Session = Depends(get_db),
):
    repo = WatchlistRepository(session)
    item = session.get(WatchlistItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    updated = repo.update(item)
    await app_state.on_watchlist_changed()
    return updated


@router.delete("/{item_id}")
async def delete_watchlist(item_id: int, session: Session = Depends(get_db)):
    repo = WatchlistRepository(session)
    item = session.get(WatchlistItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    repo.delete(item_id)
    await app_state.on_watchlist_changed()
    return {"ok": True}


@router.get("/instruments/search")
async def search_instruments(q: str, limit: int = 20):
    return await app_state.search_instruments(q, limit=limit)
