import json
from datetime import date, datetime, time
from typing import Any

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.timezone import IST, to_utc
from app.storage.models import (
    AppSetting,
    NotificationLog,
    ScannerUniverseEntry,
    Segment,
    SignalRecord,
    WatchlistItem,
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "capital_per_trade": 20000,
    "strategy_mode": "balanced",
    "buy_threshold": 65,
    "sell_threshold": 65,
    "top_n": 30,
    "universe_source": "BOTH",
    "telegram_enabled": False,
    "telegram_chat_id": "",
    "scanner_enabled": True,
    "supertrend_factor": 3.0,
    "initial_stop_atr": 1.5,
    "target1_atr": 1.5,
    "target2_atr": 3.0,
    "target3_atr": 6.0,
    "use_opening_range_filter": True,
    "max_vwap_distance_atr": 2.0,
    "strong_breakout_vwap_distance_atr": 3.0,
    "upstox_configured": False,
    "upstox_last_auth_at": "",
    "upstox_account_label": "",
}


class SettingsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> dict[str, Any]:
        rows = self.session.exec(select(AppSetting)).all()
        result = dict(DEFAULT_SETTINGS)
        settings = get_settings()
        result["capital_per_trade"] = settings.default_capital_per_trade
        result["strategy_mode"] = settings.default_strategy_mode
        result["top_n"] = settings.default_top_n
        for row in rows:
            try:
                result[row.key] = json.loads(row.value)
            except (json.JSONDecodeError, TypeError):
                result[row.key] = row.value
        return result

    def update(self, updates: dict[str, Any]) -> dict[str, Any]:
        for key, value in updates.items():
            existing = self.session.get(AppSetting, key)
            serialized = json.dumps(value)
            if existing:
                existing.value = serialized
                self.session.add(existing)
            else:
                self.session.add(AppSetting(key=key, value=serialized))
        self.session.commit()
        return self.get_all()


class WatchlistRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self, segment_id: int | None = None) -> list[WatchlistItem]:
        stmt = select(WatchlistItem)
        if segment_id is not None:
            stmt = stmt.where(WatchlistItem.segment_id == segment_id)
        return list(self.session.exec(stmt).all())

    def get_by_key(self, instrument_key: str) -> WatchlistItem | None:
        stmt = select(WatchlistItem).where(
            WatchlistItem.instrument_key == instrument_key
        )
        return self.session.exec(stmt).first()

    def create(self, item: WatchlistItem) -> WatchlistItem:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def update(self, item: WatchlistItem) -> WatchlistItem:
        item.updated_at = datetime.utcnow()
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, item_id: int) -> None:
        item = self.session.get(WatchlistItem, item_id)
        if item:
            self.session.delete(item)
            self.session.commit()

    def clear_segment(self, segment_id: int) -> None:
        rows = self.session.exec(
            select(WatchlistItem).where(WatchlistItem.segment_id == segment_id)
        ).all()
        for row in rows:
            row.segment_id = None
            self.session.add(row)
        self.session.commit()


class SegmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> list[Segment]:
        return list(self.session.exec(select(Segment).order_by(Segment.name)).all())

    def get_by_id(self, segment_id: int) -> Segment | None:
        return self.session.get(Segment, segment_id)

    def get_by_name(self, name: str) -> Segment | None:
        stmt = select(Segment).where(Segment.name == name)
        return self.session.exec(stmt).first()

    def create(self, name: str) -> Segment:
        segment = Segment(name=name)
        self.session.add(segment)
        self.session.commit()
        self.session.refresh(segment)
        return segment

    def delete(self, segment_id: int) -> None:
        segment = self.session.get(Segment, segment_id)
        if segment:
            self.session.delete(segment)
            self.session.commit()


class SignalRepository:
    def __init__(self, session: Session):
        self.session = session

    def exists_event_key(self, event_key: str) -> bool:
        stmt = select(SignalRecord).where(SignalRecord.event_key == event_key)
        return self.session.exec(stmt).first() is not None

    def create(self, signal: SignalRecord) -> SignalRecord:
        self.session.add(signal)
        self.session.commit()
        self.session.refresh(signal)
        return signal

    def list_signals(
        self,
        limit: int = 100,
        direction: str | None = None,
        symbol: str | None = None,
        archived: bool | None = None,
        outcome: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[SignalRecord]:
        stmt = select(SignalRecord).order_by(SignalRecord.generated_at_utc.desc())
        if direction:
            stmt = stmt.where(SignalRecord.direction == direction)
        if symbol:
            stmt = stmt.where(SignalRecord.symbol == symbol)
        if archived is not None:
            stmt = stmt.where(SignalRecord.archived == archived)
        if outcome:
            stmt = stmt.where(SignalRecord.outcome == outcome)
        if date_from:
            start = to_utc(datetime.combine(date.fromisoformat(date_from), time.min, tzinfo=IST))
            stmt = stmt.where(SignalRecord.generated_at_utc >= start.replace(tzinfo=None))
        if date_to:
            end = to_utc(datetime.combine(date.fromisoformat(date_to), time.max, tzinfo=IST))
            stmt = stmt.where(SignalRecord.generated_at_utc <= end.replace(tzinfo=None))
        stmt = stmt.limit(limit)
        return list(self.session.exec(stmt).all())

    def get_latest(self, limit: int = 50, include_archived: bool = False) -> list[SignalRecord]:
        stmt = select(SignalRecord).order_by(SignalRecord.generated_at_utc.desc())
        if not include_archived:
            stmt = stmt.where(SignalRecord.archived == False)  # noqa: E712
        stmt = stmt.limit(limit)
        return list(self.session.exec(stmt).all())

    def get_by_id(self, signal_id: int) -> SignalRecord | None:
        return self.session.get(SignalRecord, signal_id)

    def get_latest_open_for_symbol(self, symbol: str, direction: str = "BUY") -> SignalRecord | None:
        stmt = (
            select(SignalRecord)
            .where(SignalRecord.symbol == symbol)
            .where(SignalRecord.direction == direction)
            .where(SignalRecord.outcome == "open")
            .order_by(SignalRecord.generated_at_utc.desc())
        )
        return self.session.exec(stmt).first()

    def update(self, signal: SignalRecord) -> SignalRecord:
        self.session.add(signal)
        self.session.commit()
        self.session.refresh(signal)
        return signal

    def delete_all(self) -> int:
        rows = self.session.exec(select(SignalRecord)).all()
        count = len(rows)
        for row in rows:
            self.session.delete(row)
        self.session.commit()
        return count


class UniverseRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_session(self, session_date: str, entries: list[ScannerUniverseEntry]) -> None:
        existing = self.session.exec(
            select(ScannerUniverseEntry).where(
                ScannerUniverseEntry.session_date == session_date
            )
        ).all()
        for row in existing:
            self.session.delete(row)
        for entry in entries:
            self.session.add(entry)
        self.session.commit()

    def get_session(self, session_date: str) -> list[ScannerUniverseEntry]:
        stmt = (
            select(ScannerUniverseEntry)
            .where(ScannerUniverseEntry.session_date == session_date)
            .order_by(ScannerUniverseEntry.rank)
        )
        return list(self.session.exec(stmt).all())


class NotificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def log(
        self,
        signal_id: int | None,
        channel: str,
        status: str,
        error_message: str = "",
    ) -> NotificationLog:
        entry = NotificationLog(
            signal_id=signal_id,
            channel=channel,
            status=status,
            error_message=error_message,
        )
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def mark_signal_sent(self, signal: SignalRecord) -> None:
        signal.telegram_sent = True
        signal.telegram_sent_at = datetime.utcnow()
        self.session.add(signal)
        self.session.commit()

    def delete_all(self) -> None:
        rows = self.session.exec(select(NotificationLog)).all()
        for row in rows:
            self.session.delete(row)
        self.session.commit()
