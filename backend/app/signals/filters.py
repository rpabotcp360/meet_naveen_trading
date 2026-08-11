from app.signals.naveen_v3 import IndicatorSnapshot, StrategyConfig
from app.signals.scoring import ScoreResult, compute_scores


def opening_range_filter_passed(snap: IndicatorSnapshot, config: StrategyConfig) -> bool:
    if not config.use_opening_range_filter:
        return True
    return snap.above_opening_range


def vwap_overextension_ok(snap: IndicatorSnapshot, config: StrategyConfig) -> bool:
    bullish_breakout = snap.close > snap.previous_resistance if snap.previous_resistance else False
    volume_spike = snap.volume > snap.average_volume * config.volume_multiplier
    strong_breakout = bullish_breakout and volume_spike
    allowed = (
        config.strong_breakout_vwap_distance_atr
        if strong_breakout
        else config.max_vwap_distance_atr
    )
    distance = abs(snap.close - snap.vwap)
    return distance <= snap.atr * allowed if snap.atr > 0 else True


def evaluate_buy(
    snap: IndicatorSnapshot,
    scores: ScoreResult,
    config: StrategyConfig,
    in_entry_session: bool,
) -> bool:
    """Mirrors the Pine Script's `longSetup` — the raw setup condition,
    evaluated fresh every candle. It does NOT by itself mean a new trade
    should be entered; see app.signals.position for the fresh-signal +
    cooldown + flat-position gating that turns this into an actual entry."""
    if not in_entry_session:
        return False
    if not opening_range_filter_passed(snap, config):
        return False
    if scores.buy_score < config.buy_threshold:
        return False
    if scores.buy_score <= scores.sell_score:
        return False
    if not (snap.fast_ema > snap.slow_ema):
        return False
    if not (snap.close > snap.vwap):
        return False
    if not vwap_overextension_ok(snap, config):
        return False
    return True


def evaluate_sell(
    snap: IndicatorSnapshot,
    scores: ScoreResult,
    config: StrategyConfig,
    in_entry_session: bool,
) -> bool:
    if not in_entry_session:
        return False
    if scores.sell_score < config.sell_threshold:
        return False
    if scores.sell_score <= scores.buy_score:
        return False
    if not (snap.fast_ema < snap.slow_ema):
        return False
    if not (snap.close < snap.vwap):
        return False
    distance = abs(snap.close - snap.vwap)
    allowed = config.max_vwap_distance_atr
    if snap.atr > 0 and distance > snap.atr * allowed:
        return False
    return True
