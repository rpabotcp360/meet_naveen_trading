from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from app.core.timezone import to_utc
from app.indicators.core import (
    atr,
    ema,
    macd,
    relative_volume,
    rsi,
    sma,
    supertrend,
    vwap,
)
from app.indicators.htf import compute_htf_bias


@dataclass
class OpeningRangeState:
    high: float | None = None
    low: float | None = None
    session_date: str = ""


@dataclass
class IndicatorSnapshot:
    fast_ema: float = 0.0
    slow_ema: float = 0.0
    trend_ema: float = 0.0
    vwap: float = 0.0
    rsi: float = 0.0
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    supertrend_value: float = 0.0
    supertrend_direction: int = 0
    atr: float = 0.0
    average_volume: float = 0.0
    rvol: float = 0.0
    previous_resistance: float = 0.0
    previous_support: float = 0.0
    htf_bullish: bool = False
    htf_bearish: bool = False
    opening_range_high: float | None = None
    opening_range_low: float | None = None
    opening_range_ready: bool = False
    above_opening_range: bool = False
    close: float = 0.0
    volume: float = 0.0


@dataclass
class StrategyConfig:
    fast_ema_length: int = 9
    slow_ema_length: int = 21
    trend_ema_length: int = 200
    rsi_length: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    supertrend_factor: float = 3.0
    supertrend_atr_length: int = 10
    volume_length: int = 20
    volume_multiplier: float = 1.3
    breakout_length: int = 20
    atr_length: int = 14
    htf_ema_length: int = 50
    buy_threshold: int = 65
    sell_threshold: int = 65
    initial_stop_atr: float = 1.5
    target1_atr: float = 1.5
    target2_atr: float = 3.0
    target3_atr: float = 6.0
    use_opening_range_filter: bool = True
    max_vwap_distance_atr: float = 2.0
    strong_breakout_vwap_distance_atr: float = 3.0
    trailing_stop_atr: float = 1.5
    breakeven_trigger_atr: float = 1.0
    cooldown_bars: int = 3
    capital_per_trade: float = 20000.0
    mode: str = "balanced"


MODE_PRESETS = {
    "aggressive": {"buy_threshold": 58, "sell_threshold": 58, "supertrend_factor": 2.5},
    "balanced": {"buy_threshold": 65, "sell_threshold": 65, "supertrend_factor": 3.0},
    "conservative": {"buy_threshold": 78, "sell_threshold": 78, "supertrend_factor": 3.5},
}


def apply_mode(config: StrategyConfig, mode: str) -> StrategyConfig:
    preset = MODE_PRESETS.get(mode, MODE_PRESETS["balanced"])
    config.mode = mode
    config.buy_threshold = preset["buy_threshold"]
    config.sell_threshold = preset["sell_threshold"]
    config.supertrend_factor = preset["supertrend_factor"]
    return config


def compute_snapshot(
    df_5m: pd.DataFrame,
    df_15m: pd.DataFrame,
    config: StrategyConfig,
    or_state: OpeningRangeState,
) -> IndicatorSnapshot:
    snap = IndicatorSnapshot()
    if len(df_5m) < 2:
        return snap

    close = df_5m["close"]
    high = df_5m["high"]
    low = df_5m["low"]
    volume = df_5m["volume"]

    snap.close = float(close.iloc[-1])
    snap.volume = float(volume.iloc[-1])

    snap.fast_ema = float(ema(close, config.fast_ema_length).iloc[-1])
    snap.slow_ema = float(ema(close, config.slow_ema_length).iloc[-1])
    snap.trend_ema = float(ema(close, config.trend_ema_length).iloc[-1])

    # VWAP must reset every session (matches Pine's ta.vwap()) — df_5m holds
    # weeks of history for EMA/ATR warm-up, so slice to just today's rows or
    # the cumulative sum drags in the entire multi-day history.
    if "session_date" in df_5m.columns:
        vwap_rows = df_5m[df_5m["session_date"] == df_5m["session_date"].iloc[-1]]
    else:
        vwap_rows = df_5m
    snap.vwap = float(
        vwap(vwap_rows["high"], vwap_rows["low"], vwap_rows["close"], vwap_rows["volume"]).iloc[-1]
    )

    snap.rsi = float(rsi(close, config.rsi_length).iloc[-1])

    macd_line, macd_signal, macd_hist = macd(
        close, config.macd_fast, config.macd_slow, config.macd_signal
    )
    snap.macd_line = float(macd_line.iloc[-1])
    snap.macd_signal = float(macd_signal.iloc[-1])
    snap.macd_histogram = float(macd_hist.iloc[-1])

    st_val, st_dir = supertrend(
        high, low, close, config.supertrend_factor, config.supertrend_atr_length
    )
    snap.supertrend_value = float(st_val.iloc[-1])
    snap.supertrend_direction = int(st_dir.iloc[-1])

    snap.atr = float(atr(high, low, close, config.atr_length).iloc[-1])
    snap.average_volume = float(sma(volume, config.volume_length).iloc[-1])
    snap.rvol = float(relative_volume(volume, config.volume_length).iloc[-1])

    if len(df_5m) > config.breakout_length + 1:
        snap.previous_resistance = float(
            high.iloc[-(config.breakout_length + 1) : -1].max()
        )
        snap.previous_support = float(
            low.iloc[-(config.breakout_length + 1) : -1].min()
        )

    if len(df_15m) >= 2:
        snap.htf_bullish, snap.htf_bearish = compute_htf_bias(
            df_15m, config.htf_ema_length
        )

    snap.opening_range_high = or_state.high
    snap.opening_range_low = or_state.low
    snap.opening_range_ready = or_state.high is not None and or_state.low is not None
    if snap.opening_range_ready and or_state.high is not None:
        snap.above_opening_range = snap.close > or_state.high

    return snap
