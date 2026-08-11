import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length, min_periods=1).mean()


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(
    high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14
) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()


def supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    factor: float = 3.0,
    atr_length: int = 10,
) -> tuple[pd.Series, pd.Series]:
    atr_vals = atr(high, low, close, atr_length)
    hl2 = (high + low) / 2
    upper_band = hl2 + factor * atr_vals
    lower_band = hl2 - factor * atr_vals

    st = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)

    st.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(close)):
        prev_st = st.iloc[i - 1]
        prev_dir = direction.iloc[i - 1]

        curr_upper = upper_band.iloc[i]
        curr_lower = lower_band.iloc[i]
        curr_close = close.iloc[i]

        if prev_dir == -1:
            curr_lower = max(curr_lower, prev_st)
        else:
            curr_upper = min(curr_upper, prev_st)

        if prev_dir == -1:
            if curr_close <= curr_lower:
                direction.iloc[i] = -1
                st.iloc[i] = curr_lower
            else:
                direction.iloc[i] = 1
                st.iloc[i] = curr_upper
        else:
            if curr_close >= curr_upper:
                direction.iloc[i] = 1
                st.iloc[i] = curr_upper
            else:
                direction.iloc[i] = -1
                st.iloc[i] = curr_lower

    return st, direction


def vwap(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> pd.Series:
    typical = (high + low + close) / 3
    cum_vol = volume.cumsum()
    cum_tp_vol = (typical * volume).cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def relative_volume(volume: pd.Series, length: int = 20) -> pd.Series:
    avg = sma(volume, length)
    return volume / avg.replace(0, np.nan)
