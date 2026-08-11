import uuid
from datetime import datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine
from app.storage.models import SignalRecord, WatchlistItem
from app.storage.repositories import SignalRepository, WatchlistRepository


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    from app.storage import database

    database._engine = None
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    database._engine = engine
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_signal_dedupe(session: Session):
    repo = SignalRepository(session)
    key = f"TEST|5m|{uuid.uuid4()}|BUY"
    signal = SignalRecord(
        event_key=key,
        instrument_key="NSE_EQ|TEST",
        symbol="TEST",
        direction="BUY",
        candle_timestamp_utc=datetime(2025, 1, 15, 5, 0, 0),
        entry=100,
        stop_loss=97,
        target_1=103,
        target_2=106,
        target_3=112,
        buy_score=70,
        sell_score=20,
    )
    repo.create(signal)
    assert repo.exists_event_key(signal.event_key)


def test_watchlist_crud(session: Session):
    repo = WatchlistRepository(session)
    key = f"NSE_EQ|TEST{uuid.uuid4().hex[:8]}"
    item = WatchlistItem(
        instrument_key=key,
        trading_symbol=f"TEST{uuid.uuid4().hex[:4]}",
        company_name="Reliance Industries",
    )
    created = repo.create(item)
    assert created.id is not None
    items = repo.list_all()
    assert len(items) == 1
