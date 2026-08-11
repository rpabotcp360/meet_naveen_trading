from datetime import datetime

from app.core.timezone import is_opening_range, ist_date, to_utc
from app.signals.naveen_v3 import OpeningRangeState


class OpeningRangeTracker:
    def __init__(self):
        self._states: dict[str, OpeningRangeState] = {}

    def update(self, instrument_key: str, high: float, low: float, dt: datetime) -> OpeningRangeState:
        today = str(ist_date(dt))
        state = self._states.get(instrument_key)
        if not state or state.session_date != today:
            state = OpeningRangeState(session_date=today)
            self._states[instrument_key] = state

        if is_opening_range(dt):
            if state.high is None:
                state.high = high
                state.low = low
            else:
                state.high = max(state.high, high)
                state.low = min(state.low, low)

        return state

    def get(self, instrument_key: str) -> OpeningRangeState:
        return self._states.get(instrument_key, OpeningRangeState())


def build_event_key(
    symbol: str, candle_close: datetime, direction: str, timeframe: str = "5m"
) -> str:
    ts = to_utc(candle_close).isoformat()
    return f"{symbol}|{timeframe}|{ts}|{direction}"
