"""Fixed candle dataset for signal regression testing."""

import pandas as pd
import pytest

from app.signals.filters import evaluate_buy
from app.signals.naveen_v3 import IndicatorSnapshot, StrategyConfig, compute_snapshot, OpeningRangeState
from app.signals.scoring import compute_scores


def _make_df(closes, volumes=None):
    n = len(closes)
    volumes = volumes or [1000.0] * n
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": volumes,
        }
    )


def test_regression_deterministic_scores():
    closes = [100 + i * 0.5 for i in range(250)]
    df_5m = _make_df(closes)
    df_15m = _make_df(closes[::3][:80])
    or_state = OpeningRangeState(high=100, low=98, session_date="2025-01-15")
    config = StrategyConfig()

    snap1 = compute_snapshot(df_5m, df_15m, config, or_state)
    snap2 = compute_snapshot(df_5m, df_15m, config, or_state)
    scores1 = compute_scores(snap1, config)
    scores2 = compute_scores(snap2, config)

    assert scores1.buy_score == scores2.buy_score
    assert scores1.sell_score == scores2.sell_score


def test_regression_bullish_setup_high_score():
    closes = [100 + i * 0.3 for i in range(250)]
    df_5m = _make_df(closes, [2000.0] * 250)
    df_15m = _make_df(closes[::3][:80])
    or_state = OpeningRangeState(high=100, low=98, session_date="2025-01-15")
    config = StrategyConfig()
    snap = compute_snapshot(df_5m, df_15m, config, or_state)
    snap.above_opening_range = True
    snap.opening_range_ready = True
    scores = compute_scores(snap, config)
    assert scores.buy_score >= 50
