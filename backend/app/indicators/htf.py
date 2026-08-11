import pandas as pd

from app.indicators.core import ema


def compute_htf_bias(
    htf_df: pd.DataFrame, htf_ema_length: int = 50
) -> tuple[bool, bool]:
    """Non-repainting HTF: use previous completed 15m bar close vs EMA."""
    if len(htf_df) < 2:
        return False, False
    htf_close = htf_df["close"].iloc[-2]
    htf_ema_val = ema(htf_df["close"], htf_ema_length).iloc[-2]
    htf_bullish = htf_close > htf_ema_val
    htf_bearish = htf_close < htf_ema_val
    return htf_bullish, htf_bearish
