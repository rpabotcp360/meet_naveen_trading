from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime
    app: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    expires_at: datetime


class SignupResponse(BaseModel):
    ok: bool = True
    username: str
    message: str = "Account created. Please sign in."


class SystemStatusResponse(BaseModel):
    backend: str = "ok"
    upstox_rest: str = "unknown"
    upstox_websocket: str = "unknown"
    telegram: str = "unknown"
    sqlite: str = "ok"
    frontend_websocket: str = "unknown"
    scanner_state: str = "stopped"
    subscribed_instruments: int = 0
    last_ws_message_at: Optional[datetime] = None
    last_5m_candle_at: Optional[datetime] = None
    last_15m_candle_at: Optional[datetime] = None
    uptime_seconds: float = 0
    last_error: str = ""


class SettingsUpdate(BaseModel):
    capital_per_trade: Optional[float] = None
    strategy_mode: Optional[str] = None
    buy_threshold: Optional[int] = None
    sell_threshold: Optional[int] = None
    top_n: Optional[int] = None
    universe_source: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    scanner_enabled: Optional[bool] = None
    supertrend_factor: Optional[float] = None
    initial_stop_atr: Optional[float] = None
    target1_atr: Optional[float] = None
    target2_atr: Optional[float] = None
    target3_atr: Optional[float] = None
    use_opening_range_filter: Optional[bool] = None
    max_vwap_distance_atr: Optional[float] = None
    strong_breakout_vwap_distance_atr: Optional[float] = None


class WatchlistCreate(BaseModel):
    instrument_key: str
    trading_symbol: str
    company_name: str = ""
    exchange: str = "NSE"
    enabled: bool = True
    pinned: bool = False
    segment_id: Optional[int] = None


class WatchlistUpdate(BaseModel):
    enabled: Optional[bool] = None
    pinned: Optional[bool] = None
    segment_id: Optional[int] = None


class SegmentCreate(BaseModel):
    name: str


class TelegramConfig(BaseModel):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    enabled: Optional[bool] = None


class UpstoxConfig(BaseModel):
    access_token: Optional[str] = None
    api_key: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None


class SignalResponse(BaseModel):
    id: int
    event_key: str
    instrument_key: str
    symbol: str
    company_name: str
    direction: str
    candle_timestamp_utc: datetime
    generated_at_utc: datetime
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    buy_score: int
    sell_score: int
    rvol: float
    htf_direction: str
    supertrend_direction: str
    mode: str
    universe_source: str
    quantity: int
    capital_used: float
    telegram_sent: bool
    archived: bool = False
    is_realtime: bool = True
    outcome: str = "open"


class SignalUpdate(BaseModel):
    archived: Optional[bool] = None


class ScannerLiveRow(BaseModel):
    instrument_key: str
    symbol: str
    company_name: str = ""
    ltp: float = 0.0
    change_pct: float = 0.0
    rvol: float = 0.0
    buy_score: int = 0
    sell_score: int = 0
    ema_trend: str = ""
    vwap_state: str = ""
    supertrend: str = ""
    rsi: float = 0.0
    macd_state: str = ""
    htf: str = ""
    scanner_state: str = "watching"
    source: str = "TOP30"


class InstrumentSearchResult(BaseModel):
    instrument_key: str
    trading_symbol: str
    name: str
    exchange: str
