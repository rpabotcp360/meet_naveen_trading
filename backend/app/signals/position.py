from dataclasses import dataclass

from app.market_data.candles import Candle
from app.signals.naveen_v3 import StrategyConfig


@dataclass
class TradeState:
    """Per-symbol FLAT/LONG position tracker, mirroring the Pine Script
    strategy's stateful trade management (entry, trailing stop, breakeven,
    two-leg partial exit at Target 1 / Target 2, bearish emergency exit).

    A fresh BUY notification is only produced on the bar where the setup
    condition transitions from false to true AND we are flat AND the
    cooldown since the last trade has elapsed — not on every bar the raw
    setup condition happens to hold, which is what made the naive port
    fire far more often than the reference strategy.
    """

    session_date: str = ""
    bar_index: int = -1
    prev_setup: bool = False
    last_trade_bar_index: int | None = None

    position_open: bool = False
    leg1_open: bool = False
    leg2_open: bool = False
    entry: float = 0.0
    entry_atr: float = 0.0
    trailing_stop: float = 0.0
    target1: float = 0.0
    target2: float = 0.0
    achieved: bool = False


def advance_trade_state(
    state: TradeState,
    candle: Candle,
    setup: bool,
    bearish_exit: bool,
    atr: float,
    session_date: str,
    config: StrategyConfig,
) -> tuple[bool, str | None]:
    """Advance the state machine by one completed 5m candle.

    Returns (entered_fresh, outcome). `entered_fresh` is True exactly on the
    candle where a fresh BUY entry is taken. `outcome` is set exactly once,
    on the candle where the trade fully closes: "achieved" if either target
    was hit before the position closed, "stopped" if it closed without ever
    reaching a target (stop-loss, bearish reversal, or forced flat).
    """
    if state.session_date != session_date:
        fresh = TradeState(session_date=session_date)
        state.__dict__.update(fresh.__dict__)

    state.bar_index += 1
    entered_fresh = False
    outcome: str | None = None

    fresh_setup = setup and not state.prev_setup
    cooldown_complete = (
        state.last_trade_bar_index is None
        or state.bar_index - state.last_trade_bar_index > config.cooldown_bars
    )
    if fresh_setup and not state.position_open and cooldown_complete:
        state.entry = candle.close
        state.entry_atr = atr
        state.trailing_stop = state.entry - atr * config.initial_stop_atr
        state.target1 = state.entry + atr * config.target1_atr
        state.target2 = state.entry + atr * config.target2_atr
        state.position_open = True
        state.leg1_open = True
        state.leg2_open = True
        state.achieved = False
        state.last_trade_bar_index = state.bar_index
        entered_fresh = True

    if state.position_open:
        stop_before_update = state.trailing_stop

        if candle.high >= state.entry + state.entry_atr * config.breakeven_trigger_atr:
            state.trailing_stop = max(state.trailing_stop, state.entry)

        leg1_target_hit = candle.high >= state.target1
        if state.leg1_open and (candle.low <= stop_before_update or leg1_target_hit):
            state.leg1_open = False
            if leg1_target_hit:
                state.achieved = True
                state.trailing_stop = max(state.trailing_stop, state.entry)

        leg2_target_hit = candle.high >= state.target2
        if state.leg2_open and (candle.low <= stop_before_update or leg2_target_hit):
            state.leg2_open = False
            if leg2_target_hit:
                state.achieved = True

        state.trailing_stop = max(state.trailing_stop, candle.close - atr * config.trailing_stop_atr)

        if bearish_exit:
            state.leg1_open = False
            state.leg2_open = False

        if not state.leg1_open and not state.leg2_open:
            state.position_open = False
            outcome = "achieved" if state.achieved else "stopped"

    state.prev_setup = setup
    return entered_fresh, outcome
