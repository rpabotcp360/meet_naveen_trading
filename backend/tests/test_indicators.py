import math
from datetime import datetime

import pandas as pd
import pytest

from app.core.timezone import IST, floor_to_interval, to_ist
from app.indicators.core import ema, rsi, atr, relative_volume
from app.market_data.candles import CandleBuilder
from app.signals.levels import calculate_levels
from app.signals.naveen_v3 import StrategyConfig
from app.signals.scoring import compute_scores
from app.signals.naveen_v3 import IndicatorSnapshot, compute_snapshot, OpeningRangeState
from app.signals.session import build_event_key


def test_ema_basic():
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    result = ema(s, 3)
    assert result.iloc[-1] > result.iloc[0]


def test_rsi_range():
    s = pd.Series([44, 44, 45, 46, 47, 46, 45, 44, 43, 44, 45, 46, 47, 48, 49, 50] * 3)
    result = rsi(s, 14)
    val = result.dropna().iloc[-1]
    assert 0 <= val <= 100


def test_atr_positive():
    high = pd.Series([10, 11, 12, 13, 14, 15] * 5, dtype=float)
    low = pd.Series([9, 10, 11, 12, 13, 14] * 5, dtype=float)
    close = pd.Series([9.5, 10.5, 11.5, 12.5, 13.5, 14.5] * 5, dtype=float)
    result = atr(high, low, close, 14)
    assert result.iloc[-1] > 0


def test_candle_builder_finalizes():
    builder = CandleBuilder(5)
    ts = to_ist(datetime(2025, 1, 15, 9, 15, 0))
    builder.add_tick(100, 1000, ts)
    ts2 = to_ist(datetime(2025, 1, 15, 9, 20, 0))
    finalized = builder.add_tick(101, 500, ts2)
    assert finalized is not None
    assert finalized.close == 100


def test_buy_score_max():
    snap = IndicatorSnapshot(
        close=110,
        volume=2000,
        fast_ema=105,
        slow_ema=100,
        trend_ema=90,
        vwap=100,
        rsi=60,
        macd_line=1,
        macd_signal=0,
        macd_histogram=0.5,
        supertrend_direction=-1,
        atr=2,
        average_volume=1000,
        rvol=2.0,
        previous_resistance=105,
        htf_bullish=True,
        above_opening_range=True,
        opening_range_ready=True,
    )
    config = StrategyConfig()
    scores = compute_scores(snap, config)
    assert scores.buy_score >= 65


def test_trade_levels_buy():
    config = StrategyConfig()
    levels = calculate_levels(100, 2, "BUY", config)
    assert levels.stop_loss < levels.entry
    assert levels.target_1 > levels.entry
    assert levels.quantity == math.floor(20000 / 100)


def test_event_key_deterministic():
    ts = datetime(2025, 1, 15, 5, 0, 0)
    key = build_event_key("TATASTEEL", ts, "BUY")
    assert "TATASTEEL" in key
    assert "BUY" in key


def test_ist_candle_floor():
    dt = datetime(2025, 1, 15, 9, 23, 45, tzinfo=IST)
    floored = floor_to_interval(dt, 5)
    assert floored.minute == 20
