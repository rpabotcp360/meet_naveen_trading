from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.schemas import SignalResponse, SignalUpdate
from app.services.app_state import app_state
from app.storage.database import get_db
from app.storage.repositories import SignalRepository

router = APIRouter(prefix="/signals", tags=["signals"])


def _to_response(record) -> SignalResponse:
    return SignalResponse(
        id=record.id,
        event_key=record.event_key,
        instrument_key=record.instrument_key,
        symbol=record.symbol,
        company_name=record.company_name,
        direction=record.direction,
        candle_timestamp_utc=record.candle_timestamp_utc,
        generated_at_utc=record.generated_at_utc,
        entry=record.entry,
        stop_loss=record.stop_loss,
        target_1=record.target_1,
        target_2=record.target_2,
        target_3=record.target_3,
        buy_score=record.buy_score,
        sell_score=record.sell_score,
        rvol=record.rvol,
        htf_direction=record.htf_direction,
        supertrend_direction=record.supertrend_direction,
        mode=record.mode,
        universe_source=record.universe_source,
        quantity=record.quantity,
        capital_used=record.capital_used,
        telegram_sent=record.telegram_sent,
        archived=record.archived,
        is_realtime=record.is_realtime,
        outcome=record.outcome,
    )


@router.get("")
def list_signals(
    limit: int = 100,
    direction: str | None = None,
    symbol: str | None = None,
    archived: bool | None = None,
    outcome: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    session: Session = Depends(get_db),
):
    repo = SignalRepository(session)
    return [
        _to_response(s)
        for s in repo.list_signals(limit, direction, symbol, archived, outcome, date_from, date_to)
    ]


@router.post("/reset")
async def reset_signals():
    count = await app_state.reset_all_signals()
    return {"ok": True, "deleted": count}


@router.get("/latest")
def latest_signals(
    limit: int = 50,
    include_archived: bool = False,
    session: Session = Depends(get_db),
):
    repo = SignalRepository(session)
    return [_to_response(s) for s in repo.get_latest(limit, include_archived)]


@router.get("/{signal_id}")
def get_signal(signal_id: int, session: Session = Depends(get_db)):
    repo = SignalRepository(session)
    record = repo.get_by_id(signal_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_response(record)


@router.patch("/{signal_id}")
async def update_signal(
    signal_id: int,
    payload: SignalUpdate,
    session: Session = Depends(get_db),
):
    repo = SignalRepository(session)
    record = repo.get_by_id(signal_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(record, key, value)
    updated = repo.update(record)
    if "archived" in updates:
        await app_state.browser_ws.broadcast(
            "signal_archived", {"id": updated.id, "archived": updated.archived}
        )
    return _to_response(updated)
