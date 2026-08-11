from dataclasses import dataclass

from app.signals.naveen_v3 import IndicatorSnapshot, StrategyConfig


@dataclass
class ScoreResult:
    buy_score: int = 0
    sell_score: int = 0


def compute_scores(snap: IndicatorSnapshot, config: StrategyConfig) -> ScoreResult:
    result = ScoreResult()

    ema_bullish = snap.fast_ema > snap.slow_ema
    ema_bearish = snap.fast_ema < snap.slow_ema
    major_bullish = snap.close > snap.trend_ema
    major_bearish = snap.close < snap.trend_ema
    vwap_bullish = snap.close > snap.vwap
    vwap_bearish = snap.close < snap.vwap
    st_bullish = snap.supertrend_direction < 0
    st_bearish = snap.supertrend_direction > 0
    rsi_bullish = snap.rsi > 50
    rsi_bearish = snap.rsi < 50
    macd_bullish = snap.macd_line > snap.macd_signal and snap.macd_histogram > 0
    macd_bearish = snap.macd_line < snap.macd_signal and snap.macd_histogram < 0
    volume_healthy = snap.volume > snap.average_volume
    volume_spike = snap.volume > snap.average_volume * config.volume_multiplier
    bullish_breakout = snap.close > snap.previous_resistance if snap.previous_resistance else False
    bearish_breakdown = snap.close < snap.previous_support if snap.previous_support else False

    result.buy_score += 15 if ema_bullish else 0
    result.buy_score += 15 if vwap_bullish else 0
    result.buy_score += 15 if st_bullish else 0
    result.buy_score += 10 if rsi_bullish else 0
    result.buy_score += 10 if macd_bullish else 0
    result.buy_score += 10 if volume_healthy else 0
    result.buy_score += 5 if volume_spike else 0
    result.buy_score += 10 if bullish_breakout else 0
    result.buy_score += 5 if snap.htf_bullish else 0
    result.buy_score += 5 if major_bullish else 0

    result.sell_score += 15 if ema_bearish else 0
    result.sell_score += 15 if vwap_bearish else 0
    result.sell_score += 15 if st_bearish else 0
    result.sell_score += 10 if rsi_bearish else 0
    result.sell_score += 10 if macd_bearish else 0
    result.sell_score += 10 if bearish_breakdown else 0
    result.sell_score += 5 if snap.htf_bearish else 0
    result.sell_score += 5 if major_bearish else 0

    return result
