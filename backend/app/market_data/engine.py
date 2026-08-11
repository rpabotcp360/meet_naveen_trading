import asyncio
import logging
from datetime import datetime, timedelta

import pandas as pd

from app.core.timezone import (
    candle_close_utc,
    ist_date,
    is_opening_range,
    is_signal_eligible,
    is_trading_session,
    now_utc,
    to_utc,
)
from app.market_data.candles import (
    Candle,
    SymbolCandleStore,
    _candles_to_df,
    parse_upstox_candles,
)
from app.signals.filters import evaluate_buy
from app.signals.levels import calculate_levels
from app.signals.naveen_v3 import (
    OpeningRangeState,
    StrategyConfig,
    apply_mode,
    compute_snapshot,
)
from app.signals.position import TradeState, advance_trade_state
from app.signals.scoring import compute_scores
from app.signals.session import OpeningRangeTracker, build_event_key
from app.storage.models import SignalRecord
from app.upstox.historical import UpstoxHistoricalService

logger = logging.getLogger("scanner")


def _opening_range_from_candles(candles: list[Candle]) -> OpeningRangeState:
    """Standalone opening-range calc from closed candles, for replaying a
    session that already happened — OpeningRangeTracker only updates from
    live ticks, so it can't answer this for candles seen during backfill."""
    today = ist_date()
    state = OpeningRangeState(session_date=str(today))
    for candle in candles:
        if ist_date(candle.timestamp) != today or not is_opening_range(candle.timestamp):
            continue
        if state.high is None:
            state.high = candle.high
            state.low = candle.low
        else:
            state.high = max(state.high, candle.high)
            state.low = min(state.low, candle.low)
    return state


class MarketDataEngine:
    def __init__(self):
        self.stores: dict[str, SymbolCandleStore] = {}
        self.or_tracker = OpeningRangeTracker()
        self.historical = UpstoxHistoricalService()
        self.last_5m_candle_at: datetime | None = None
        self.last_15m_candle_at: datetime | None = None
        self._symbol_meta: dict[str, dict] = {}
        self._live_rows: dict[str, dict] = {}
        self._trade_states: dict[str, TradeState] = {}

    def set_symbol_meta(self, instrument_key: str, meta: dict) -> None:
        self._symbol_meta[instrument_key] = meta

    def _get_trade_state(self, instrument_key: str) -> TradeState:
        if instrument_key not in self._trade_states:
            self._trade_states[instrument_key] = TradeState()
        return self._trade_states[instrument_key]

    def get_store(self, instrument_key: str) -> SymbolCandleStore:
        if instrument_key not in self.stores:
            self.stores[instrument_key] = SymbolCandleStore(instrument_key=instrument_key)
        return self.stores[instrument_key]

    async def backfill(self, instrument_key: str) -> None:
        store = self.get_store(instrument_key)
        to_date = now_utc().strftime("%Y-%m-%d")
        from_date = (now_utc() - timedelta(days=28)).strftime("%Y-%m-%d")
        hist = await self.historical.get_candles(
            instrument_key, "minutes", 5, from_date, to_date
        )
        store.candles_5m = parse_upstox_candles(hist)[-300:]
        intraday = await self.historical.get_intraday_candles(
            instrument_key, "minutes", 5
        )
        if intraday:
            intraday_candles = parse_upstox_candles(intraday)
            existing_ts = {c.timestamp for c in store.candles_5m}
            for c in intraday_candles:
                if c.timestamp not in existing_ts:
                    store.candles_5m.append(c)

        hist_15 = await self.historical.get_candles(
            instrument_key, "minutes", 15, from_date, to_date
        )
        store.candles_15m = parse_upstox_candles(hist_15)[-100:]
        intraday_15 = await self.historical.get_intraday_candles(
            instrument_key, "minutes", 15
        )
        if intraday_15:
            for c in parse_upstox_candles(intraday_15):
                existing = {x.timestamp for x in store.candles_15m}
                if c.timestamp not in existing:
                    store.candles_15m.append(c)

    async def on_tick(self, instrument_key: str, tick: dict) -> list[SignalRecord]:
        store = self.get_store(instrument_key)
        ltp = float(tick.get("ltp", 0))
        volume = float(tick.get("volume", 0))
        if ltp <= 0:
            return []
        store.ltp = ltp
        if tick.get("close"):
            store.prev_close = float(tick["close"])

        ts = now_utc()
        self.or_tracker.update(instrument_key, ltp, ltp, ts)

        finalized_5m = store.builder_5m.add_tick(ltp, volume, ts)
        finalized_15m = store.builder_15m.add_tick(ltp, volume, ts)

        signals = []
        if finalized_5m:
            store.candles_5m.append(finalized_5m)
            if len(store.candles_5m) > 500:
                store.candles_5m = store.candles_5m[-500:]
            self.last_5m_candle_at = candle_close_utc(finalized_5m.timestamp, 5)
            sig = self._evaluate_candle(instrument_key, finalized_5m)
            if sig:
                signals.append(sig)

        if finalized_15m:
            store.candles_15m.append(finalized_15m)
            if len(store.candles_15m) > 200:
                store.candles_15m = store.candles_15m[-200:]
            self.last_15m_candle_at = candle_close_utc(finalized_15m.timestamp, 15)

        self._update_live_row(instrument_key)
        return signals

    def _evaluate_candle(
        self,
        instrument_key: str,
        candle: Candle,
        config: StrategyConfig | None = None,
        df_5m: pd.DataFrame | None = None,
        df_15m: pd.DataFrame | None = None,
        or_state: OpeningRangeState | None = None,
        is_realtime: bool = True,
    ) -> SignalRecord | None:
        close_ts = candle_close_utc(candle.timestamp, 5)
        if not is_trading_session(close_ts):
            return None

        if config is None:
            from app.services.app_state import app_state

            config = app_state.get_strategy_config()

        store = self.get_store(instrument_key)
        if df_5m is None:
            df_5m = store.to_df_5m()
        if df_15m is None:
            df_15m = store.to_df_15m()
        if or_state is None:
            or_state = self.or_tracker.get(instrument_key)
        snap = compute_snapshot(df_5m, df_15m, config, or_state)
        scores = compute_scores(snap, config)

        # Raw setup condition (Pine `longSetup`) — true whenever the rules
        # currently qualify, independent of whether we already hold a trade.
        in_entry_session = is_signal_eligible(close_ts)
        setup = evaluate_buy(snap, scores, config, in_entry_session)

        # Bearish emergency exit (Pine `bearishExitSignal`) — only relevant
        # while a position is open; deliberately reuses buy_threshold, not
        # sell_threshold, to match the reference strategy exactly.
        bearish_exit = (
            scores.sell_score >= config.buy_threshold
            and scores.sell_score > scores.buy_score
            and snap.fast_ema < snap.slow_ema
            and snap.close < snap.vwap
        )

        state = self._get_trade_state(instrument_key)
        meta = self._symbol_meta.get(instrument_key, {})
        symbol = meta.get("trading_symbol", instrument_key)
        entered, outcome = advance_trade_state(
            state,
            candle,
            setup,
            bearish_exit,
            snap.atr,
            session_date=str(ist_date(candle.timestamp)),
            config=config,
        )
        if not entered:
            if outcome:
                self._record_outcome(symbol, outcome)
            return None

        levels = calculate_levels(state.entry, state.entry_atr, "BUY", config)
        event_key = build_event_key(symbol, close_ts, "BUY")

        return SignalRecord(
            event_key=event_key,
            instrument_key=instrument_key,
            symbol=symbol,
            company_name=meta.get("company_name", ""),
            direction="BUY",
            candle_timestamp_utc=to_utc(candle.timestamp),
            generated_at_utc=close_ts,
            entry=levels.entry,
            stop_loss=levels.stop_loss,
            target_1=levels.target_1,
            target_2=levels.target_2,
            target_3=levels.target_3,
            buy_score=scores.buy_score,
            sell_score=scores.sell_score,
            rvol=snap.rvol,
            rsi=snap.rsi,
            atr=snap.atr,
            vwap=snap.vwap,
            ema_fast=snap.fast_ema,
            ema_slow=snap.slow_ema,
            ema_major=snap.trend_ema,
            htf_direction="Bullish" if snap.htf_bullish else "Bearish",
            supertrend_direction="Bullish" if snap.supertrend_direction < 0 else "Bearish",
            mode=config.mode,
            universe_source=meta.get("source", "TOP30"),
            quantity=levels.quantity,
            capital_used=levels.capital_used,
            is_realtime=is_realtime,
        )

    def _record_outcome(self, symbol: str, outcome: str) -> None:
        """Persist how the most recent open trade for this symbol concluded
        (target hit vs stopped out). Since only one BUY position can be open
        per symbol at a time, "the latest open signal" is unambiguous."""
        from app.storage.database import session_scope
        from app.storage.repositories import SignalRepository

        with session_scope() as session:
            repo = SignalRepository(session)
            record = repo.get_latest_open_for_symbol(symbol)
            if not record:
                return
            record.outcome = outcome
            updated = repo.update(record)

        from app.services.app_state import app_state

        asyncio.create_task(
            app_state.browser_ws.broadcast(
                "signal_outcome_updated", {"id": updated.id, "symbol": symbol, "outcome": outcome}
            )
        )

    def evaluate_today_history(
        self, instrument_key: str, config: StrategyConfig
    ) -> list[SignalRecord]:
        """Replay every closed 5m candle from today's session through the same
        stateful entry/exit logic used live, so signals that would have fired
        before the scanner was started (e.g. started mid-day) aren't silently
        missed. Always replays from a clean FLAT state — each scanner start
        deterministically re-derives today's position history from scratch,
        so a restart mid-day doesn't corrupt cooldown/position bookkeeping."""
        self._trade_states[instrument_key] = TradeState()
        store = self.get_store(instrument_key)
        candles = store.candles_5m
        today = ist_date()
        or_state = _opening_range_from_candles(candles)

        signals = []
        for idx, candle in enumerate(candles):
            close_ts = candle_close_utc(candle.timestamp, 5)
            if ist_date(candle.timestamp) != today:
                continue
            if not is_trading_session(close_ts):
                continue
            df_5m = _candles_to_df(candles[: idx + 1])
            df_15m = _candles_to_df(
                [c for c in store.candles_15m if c.timestamp <= candle.timestamp]
            )
            sig = self._evaluate_candle(
                instrument_key,
                candle,
                config=config,
                df_5m=df_5m,
                df_15m=df_15m,
                or_state=or_state,
                is_realtime=False,
            )
            if sig:
                signals.append(sig)
        return signals

    def _update_live_row(self, instrument_key: str) -> None:
        from app.services.app_state import app_state

        store = self.get_store(instrument_key)
        config = app_state.get_strategy_config()
        meta = self._symbol_meta.get(instrument_key, {})
        or_state = self.or_tracker.get(instrument_key)
        snap = compute_snapshot(
            store.to_df_5m(), store.to_df_15m(), config, or_state
        )
        scores = compute_scores(snap, config)
        change_pct = 0.0
        if store.prev_close > 0 and store.ltp > 0:
            change_pct = ((store.ltp - store.prev_close) / store.prev_close) * 100

        self._live_rows[instrument_key] = {
            "instrument_key": instrument_key,
            "symbol": meta.get("trading_symbol", instrument_key),
            "company_name": meta.get("company_name", ""),
            "ltp": store.ltp,
            "change_pct": round(change_pct, 2),
            "rvol": round(snap.rvol, 2),
            "buy_score": scores.buy_score,
            "sell_score": scores.sell_score,
            "ema_trend": "Bullish" if snap.fast_ema > snap.slow_ema else "Bearish",
            "vwap_state": "Above" if store.ltp > snap.vwap else "Below",
            "supertrend": "Bullish" if snap.supertrend_direction < 0 else "Bearish",
            "rsi": round(snap.rsi, 1),
            "macd_state": "Bullish" if snap.macd_histogram > 0 else "Bearish",
            "htf": "Bullish" if snap.htf_bullish else "Bearish",
            "scanner_state": "watching",
            "source": meta.get("source", "TOP30"),
        }

    def get_live_rows(self) -> list[dict]:
        return list(self._live_rows.values())

    def clear_live_rows(self) -> None:
        """Wipe the live scanner table. Called on stop so a changed
        watchlist/universe-source setting doesn't leave stale rows from the
        previous run visible until the whole backend process restarts."""
        self._live_rows.clear()
