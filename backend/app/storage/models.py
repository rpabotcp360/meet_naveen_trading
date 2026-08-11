from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class StrategyMode(str, Enum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class UniverseSource(str, Enum):
    TOP30 = "TOP30"
    WATCHLIST = "WATCHLIST"
    BOTH = "BOTH"


class Segment(SQLModel, table=True):
    __tablename__ = "segments"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WatchlistItem(SQLModel, table=True):
    __tablename__ = "watchlist"

    id: Optional[int] = Field(default=None, primary_key=True)
    instrument_key: str = Field(index=True, unique=True)
    trading_symbol: str
    company_name: str = ""
    exchange: str = "NSE"
    enabled: bool = True
    pinned: bool = False
    segment_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SignalRecord(SQLModel, table=True):
    __tablename__ = "signals"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_key: str = Field(unique=True, index=True)
    instrument_key: str = Field(index=True)
    symbol: str
    company_name: str = ""
    direction: str
    candle_timestamp_utc: datetime
    generated_at_utc: datetime = Field(default_factory=datetime.utcnow)
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    buy_score: int
    sell_score: int
    rvol: float = 0.0
    rsi: float = 0.0
    atr: float = 0.0
    vwap: float = 0.0
    ema_fast: float = 0.0
    ema_slow: float = 0.0
    ema_major: float = 0.0
    htf_direction: str = ""
    supertrend_direction: str = ""
    mode: str = "balanced"
    universe_source: str = "TOP30"
    quantity: int = 0
    capital_used: float = 0.0
    telegram_sent: bool = False
    telegram_sent_at: Optional[datetime] = None
    archived: bool = False
    is_realtime: bool = True
    outcome: str = "open"


class ScannerUniverseEntry(SQLModel, table=True):
    __tablename__ = "scanner_universe"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_date: str = Field(index=True)
    instrument_key: str
    symbol: str
    rank: int
    rank_score: float = 0.0
    source: str = "TOP30"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AppSetting(SQLModel, table=True):
    __tablename__ = "app_settings"

    key: str = Field(primary_key=True)
    value: str


class NotificationLog(SQLModel, table=True):
    __tablename__ = "notification_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    signal_id: Optional[int] = None
    channel: str = "telegram"
    status: str
    error_message: str = ""
    attempted_at: datetime = Field(default_factory=datetime.utcnow)


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_sessions"

    token: str = Field(primary_key=True)
    username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
