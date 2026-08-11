from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from app.core.timezone import floor_to_interval, to_ist, to_utc


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime  # candle open in IST


@dataclass
class CandleBuilder:
    interval_minutes: int
    active: Candle | None = None

    def add_tick(
        self, price: float, volume: float, ts: datetime
    ) -> Candle | None:
        bucket_start = floor_to_interval(ts, self.interval_minutes)
        finalized = None

        if self.active is None:
            self.active = Candle(
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                timestamp=bucket_start,
            )
            return None

        if bucket_start > self.active.timestamp:
            finalized = self.active
            self.active = Candle(
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                timestamp=bucket_start,
            )
            return finalized

        self.active.high = max(self.active.high, price)
        self.active.low = min(self.active.low, price)
        self.active.close = price
        self.active.volume += volume
        return None

    def force_finalize(self) -> Candle | None:
        finalized = self.active
        self.active = None
        return finalized


@dataclass
class SymbolCandleStore:
    instrument_key: str
    builder_5m: CandleBuilder = field(default_factory=lambda: CandleBuilder(5))
    builder_15m: CandleBuilder = field(default_factory=lambda: CandleBuilder(15))
    candles_5m: list[Candle] = field(default_factory=list)
    candles_15m: list[Candle] = field(default_factory=list)
    ltp: float = 0.0
    prev_close: float = 0.0

    def to_df_5m(self) -> pd.DataFrame:
        return _candles_to_df(self.candles_5m)

    def to_df_15m(self) -> pd.DataFrame:
        return _candles_to_df(self.candles_15m)


def _candles_to_df(candles: list[Candle]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "session_date"])
    return pd.DataFrame(
        {
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
            # candle.timestamp is already IST-localized (see parse_upstox_candles) —
            # this lets VWAP reset every session instead of accumulating across
            # the many weeks of history kept for EMA/ATR warm-up.
            "session_date": [c.timestamp.strftime("%Y-%m-%d") for c in candles],
        }
    )


def parse_upstox_candles(raw: list[list]) -> list[Candle]:
    candles = []
    for row in reversed(raw):
        if len(row) < 6:
            continue
        ts = pd.Timestamp(row[0]).to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=to_utc(datetime.utcnow()).tzinfo)
        candles.append(
            Candle(
                timestamp=to_ist(ts),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
        )
    return candles
