import asyncio
import logging
from datetime import datetime

from sqlmodel import Session

from app.api.schemas import SystemStatusResponse, TelegramConfig, UpstoxConfig
from app.core.config import get_settings
from app.core.secrets import (
    TELEGRAM_BOT_TOKEN,
    UPSTOX_ACCESS_TOKEN,
    UPSTOX_CLIENT_SECRET,
    delete_secret,
    get_secret,
    has_secret,
    set_secret,
)
from app.core.timezone import ist_date, now_utc
from app.market_data.engine import MarketDataEngine
from app.notifications.telegram import TelegramNotifier
from app.scheduler.scanner_scheduler import ScannerScheduler
from app.signals.naveen_v3 import StrategyConfig, apply_mode
from app.storage.database import get_db, init_db, session_scope
from app.storage.models import ScannerUniverseEntry, SignalRecord
from app.storage.repositories import (
    NotificationRepository,
    SettingsRepository,
    SignalRepository,
    UniverseRepository,
    WatchlistRepository,
)
from app.universe.ranker import UniverseRanker
from app.upstox.auth import UpstoxAuthService
from app.upstox.instruments import UpstoxInstrumentService
from app.upstox.market_status import UpstoxMarketStatusService
from app.upstox.websocket_v3 import UpstoxWebSocketService
from app.websocket.broadcaster import BrowserWebSocketManager

logger = logging.getLogger("app")

LIVE_ROWS_BROADCAST_INTERVAL_SECONDS = 2.0


class AppState:
    def __init__(self):
        self.started_at = now_utc()
        self.scanner_state = "stopped"
        self.allow_new_signals = True
        self.backfill_done = 0
        self.backfill_total = 0
        self._scanner_start_task: asyncio.Task | None = None
        self.last_error = ""
        self.universe: list[dict] = []
        self._last_live_broadcast = 0.0
        self.buy_signals_today = 0
        self.sell_signals_today = 0

        self.auth = UpstoxAuthService()
        self.instruments = UpstoxInstrumentService()
        self.market_status = UpstoxMarketStatusService()
        self.ranker = UniverseRanker()
        self.market_engine = MarketDataEngine()
        self.upstox_ws = UpstoxWebSocketService()
        self.browser_ws = BrowserWebSocketManager()
        self.telegram = TelegramNotifier()
        self.scheduler: ScannerScheduler | None = None

        self.upstox_ws.set_callback(self._on_upstox_tick)

    def get_strategy_config(self) -> StrategyConfig:
        with session_scope() as session:
            settings = SettingsRepository(session).get_all()
            config = StrategyConfig(
                buy_threshold=int(settings.get("buy_threshold", 65)),
                sell_threshold=int(settings.get("sell_threshold", 65)),
                supertrend_factor=float(settings.get("supertrend_factor", 3.0)),
                initial_stop_atr=float(settings.get("initial_stop_atr", 1.5)),
                target1_atr=float(settings.get("target1_atr", 1.5)),
                target2_atr=float(settings.get("target2_atr", 3.0)),
                target3_atr=float(settings.get("target3_atr", 6.0)),
                use_opening_range_filter=bool(settings.get("use_opening_range_filter", True)),
                max_vwap_distance_atr=float(settings.get("max_vwap_distance_atr", 2.0)),
                strong_breakout_vwap_distance_atr=float(
                    settings.get("strong_breakout_vwap_distance_atr", 3.0)
                ),
                capital_per_trade=float(settings.get("capital_per_trade", 20000)),
            )
            return apply_mode(config, str(settings.get("strategy_mode", "balanced")))

    async def startup(self) -> None:
        init_db()
        self.scheduler = ScannerScheduler(self)
        self.scheduler.start()
        settings = get_settings()
        if settings.upstox_api_key:
            self.auth.settings.upstox_api_key = settings.upstox_api_key
        self._bootstrap_auth_from_env()
        self._bootstrap_upstox_token_from_env()

    def _bootstrap_auth_from_env(self) -> None:
        from app.core.auth import credentials_configured, set_credentials

        if credentials_configured():
            return
        settings = get_settings()
        username = settings.auth_username.strip()
        password = settings.auth_password.strip()
        if username and password:
            set_credentials(username, password)

    def _bootstrap_upstox_token_from_env(self) -> None:
        if self.auth.is_authenticated():
            return
        settings = get_settings()
        token = settings.upstox_api_key.strip()
        if token.startswith("eyJ"):
            self.auth.set_access_token(token)
            with session_scope() as session:
                SettingsRepository(session).update(
                    {
                        "upstox_configured": True,
                        "upstox_auth_mode": "analytics_token",
                        "upstox_last_auth_at": now_utc().isoformat(),
                    }
                )

    async def shutdown(self) -> None:
        await self.stop_scanner()
        if self.scheduler:
            self.scheduler.shutdown()

    async def _on_upstox_tick(self, instrument_key: str, tick: dict) -> None:
        if self.scanner_state != "running":
            return
        if self.upstox_ws.is_stale():
            self.scanner_state = "degraded"
            return
        if not self.allow_new_signals:
            return
        try:
            signals = await self.market_engine.on_tick(instrument_key, tick)
            for signal in signals:
                await self._process_signal(signal)
            await self._maybe_broadcast_live_rows()
        except Exception as exc:
            self.last_error = str(exc)
            logger.exception("Tick processing error")

    async def _maybe_broadcast_live_rows(self) -> None:
        loop_time = asyncio.get_event_loop().time()
        if loop_time - self._last_live_broadcast < LIVE_ROWS_BROADCAST_INTERVAL_SECONDS:
            return
        self._last_live_broadcast = loop_time
        await self.browser_ws.broadcast("live_rows_update", self.market_engine.get_live_rows())

    async def _process_signal(self, signal: SignalRecord) -> None:
        with session_scope() as session:
            repo = SignalRepository(session)
            if repo.exists_event_key(signal.event_key):
                return
            saved = repo.create(signal)
            if saved.direction == "BUY":
                self.buy_signals_today += 1
            else:
                self.sell_signals_today += 1

            settings = SettingsRepository(session).get_all()
            if settings.get("telegram_enabled") and settings.get("telegram_chat_id"):
                await self.telegram.notify_signal(
                    saved, str(settings["telegram_chat_id"]), session, repo
                )

            await self.browser_ws.broadcast(
                "signal_created",
                {
                    "id": saved.id,
                    "symbol": saved.symbol,
                    "direction": saved.direction,
                    "entry": saved.entry,
                    "stop_loss": saved.stop_loss,
                    "target_1": saved.target_1,
                    "target_2": saved.target_2,
                    "target_3": saved.target_3,
                    "buy_score": saved.buy_score,
                    "sell_score": saved.sell_score,
                    "rvol": saved.rvol,
                    "htf_direction": saved.htf_direction,
                    "universe_source": saved.universe_source,
                    "candle_timestamp_utc": saved.candle_timestamp_utc.isoformat(),
                    "generated_at_utc": saved.generated_at_utc.isoformat(),
                    "archived": saved.archived,
                    "is_realtime": saved.is_realtime,
                    "quantity": saved.quantity,
                    "capital_used": saved.capital_used,
                    "outcome": saved.outcome,
                },
            )
            await self.browser_ws.broadcast("scanner_status", self.get_scanner_status())

    async def reset_all_signals(self) -> int:
        with session_scope() as session:
            count = SignalRepository(session).delete_all()
            NotificationRepository(session).delete_all()
        self.buy_signals_today = 0
        self.sell_signals_today = 0
        await self.browser_ws.broadcast("signals_reset", {})
        await self.browser_ws.broadcast("scanner_status", self.get_scanner_status())
        return count

    async def start_scanner(self) -> None:
        if not self.auth.is_authenticated():
            raise RuntimeError("Upstox not authenticated")
        if self.scanner_state in ("starting", "running"):
            return
        self.scanner_state = "starting"
        self.backfill_done = 0
        self.backfill_total = 0
        await self.browser_ws.broadcast("scanner_status", self.get_scanner_status())
        self._scanner_start_task = asyncio.create_task(self._run_scanner_start())

    async def _run_scanner_start(self) -> None:
        try:
            await self.refresh_universe()
            self.backfill_total = len(self.universe)
            await self.browser_ws.broadcast("scanner_status", self.get_scanner_status())
            strategy_config = self.get_strategy_config()
            for idx, item in enumerate(self.universe, start=1):
                key = item["instrument_key"]
                self.market_engine.set_symbol_meta(key, item)
                await self.market_engine.backfill(key)
                for signal in self.market_engine.evaluate_today_history(key, strategy_config):
                    await self._process_signal(signal)
                self.backfill_done = idx
                await self.browser_ws.broadcast("scanner_status", self.get_scanner_status())
            keys = [u["instrument_key"] for u in self.universe]
            await self.upstox_ws.start()
            await self.upstox_ws.subscribe(keys)
            self.scanner_state = "running"
            self.allow_new_signals = True
        except asyncio.CancelledError:
            self.scanner_state = "stopped"
            raise
        except Exception as exc:
            self.last_error = str(exc)
            self.scanner_state = "stopped"
            logger.exception("Scanner start failed")
        await self.browser_ws.broadcast("scanner_status", self.get_scanner_status())

    async def stop_scanner(self) -> None:
        if self._scanner_start_task and not self._scanner_start_task.done():
            self._scanner_start_task.cancel()
            try:
                await self._scanner_start_task
            except asyncio.CancelledError:
                pass
            self._scanner_start_task = None
        await self.upstox_ws.stop()
        self.scanner_state = "stopped"
        self.backfill_done = 0
        self.backfill_total = 0
        self.universe = []
        self.market_engine.clear_live_rows()
        await self.browser_ws.broadcast("scanner_status", self.get_scanner_status())
        await self.browser_ws.broadcast("live_rows_update", self.market_engine.get_live_rows())

    async def refresh_universe(self) -> None:
        with session_scope() as session:
            settings = SettingsRepository(session).get_all()
            top_n = int(settings.get("top_n", 30))
            universe_source = str(settings.get("universe_source", "BOTH")).upper()
            watchlist = WatchlistRepository(session).list_all()

        top30 = await self.ranker.rank_top_n(top_n) if universe_source != "WATCHLIST" else []
        effective_watchlist = watchlist if universe_source != "TOP30" else []
        merged = await self.ranker.merge_with_watchlist(top30, effective_watchlist)
        normalized = []
        for item in merged:
            key = await self.instruments.resolve_instrument_key(
                item["instrument_key"], item.get("trading_symbol", "")
            )
            normalized.append({**item, "instrument_key": key})
        self.universe = normalized

        today = str(ist_date())
        entries = [
            ScannerUniverseEntry(
                session_date=today,
                instrument_key=u["instrument_key"],
                symbol=u["trading_symbol"],
                rank=u.get("rank", 0),
                rank_score=u.get("rank_score", 0),
                source=u.get("source", "TOP30"),
            )
            for u in normalized
        ]
        with session_scope() as session:
            UniverseRepository(session).save_session(today, entries)

    async def on_watchlist_changed(self) -> None:
        asyncio.create_task(self.refresh_universe())

    def get_scanner_status(self) -> dict:
        return {
            "state": self.scanner_state,
            "symbols_scanned": len(self.universe),
            "backfill_done": self.backfill_done,
            "backfill_total": self.backfill_total,
            "buy_signals_today": self.buy_signals_today,
            "sell_signals_today": self.sell_signals_today,
            "allow_new_signals": self.allow_new_signals,
            "last_5m_candle_at": self.market_engine.last_5m_candle_at,
            "last_15m_candle_at": self.market_engine.last_15m_candle_at,
            "auto_mode": self.scheduler.get_auto_mode_status() if self.scheduler else {"enabled": False},
        }

    def get_universe(self) -> list[dict]:
        return self.universe

    def get_live_rows(self) -> list[dict]:
        return self.market_engine.get_live_rows()

    def get_system_status(self) -> SystemStatusResponse:
        uptime = (now_utc() - self.started_at).total_seconds()
        return SystemStatusResponse(
            backend="ok",
            upstox_rest="connected" if self.auth.is_authenticated() else "disconnected",
            upstox_websocket=self.upstox_ws.state,
            telegram="configured" if has_secret(TELEGRAM_BOT_TOKEN) else "not_configured",
            sqlite="ok",
            frontend_websocket=self.browser_ws.state,
            scanner_state=self.scanner_state,
            subscribed_instruments=len(self.universe),
            last_ws_message_at=self.upstox_ws.last_message_at,
            last_5m_candle_at=self.market_engine.last_5m_candle_at,
            last_15m_candle_at=self.market_engine.last_15m_candle_at,
            uptime_seconds=uptime,
            last_error=self.last_error,
        )

    def get_upstox_status(self, session: Session) -> dict:
        settings = SettingsRepository(session).get_all()
        return {
            "configured": self.auth.is_authenticated() or bool(settings.get("upstox_configured")),
            "authenticated": self.auth.is_authenticated(),
            "auth_mode": self.auth.auth_mode(),
            "last_auth_at": settings.get("upstox_last_auth_at", ""),
            "account_label": settings.get("upstox_account_label", "Analytics Token"),
            "redirect_uri": get_settings().upstox_redirect_uri,
            "websocket_state": self.upstox_ws.state,
        }

    def configure_upstox(self, payload: UpstoxConfig, session: Session) -> dict:
        settings_repo = SettingsRepository(session)
        updates: dict = {"upstox_configured": True}

        if payload.access_token:
            self.auth.set_access_token(payload.access_token)
            updates["upstox_auth_mode"] = "analytics_token"
            updates["upstox_last_auth_at"] = now_utc().isoformat()
        if payload.api_key and not payload.api_key.startswith("eyJ"):
            get_settings().upstox_api_key = payload.api_key
        elif payload.api_key and payload.api_key.startswith("eyJ"):
            self.auth.set_access_token(payload.api_key)
            updates["upstox_auth_mode"] = "analytics_token"
            updates["upstox_last_auth_at"] = now_utc().isoformat()
        if payload.client_secret:
            set_secret(UPSTOX_CLIENT_SECRET, payload.client_secret)
            updates["upstox_auth_mode"] = "oauth"
        if payload.redirect_uri:
            get_settings().upstox_redirect_uri = payload.redirect_uri

        settings_repo.update(updates)
        return self.get_upstox_status(session)

    def get_upstox_login_url(self) -> str:
        return self.auth.get_login_url()

    async def handle_upstox_callback(self, code: str, session: Session) -> None:
        token_data = await self.auth.exchange_code(code)
        access_token = token_data.get("access_token", "")
        if access_token:
            set_secret(UPSTOX_ACCESS_TOKEN, access_token)
        SettingsRepository(session).update(
            {
                "upstox_configured": True,
                "upstox_last_auth_at": now_utc().isoformat(),
            }
        )

    def disconnect_upstox(self, session: Session) -> None:
        delete_secret(UPSTOX_ACCESS_TOKEN)
        SettingsRepository(session).update({"upstox_configured": False})

    def get_telegram_status(self, session: Session) -> dict:
        settings = SettingsRepository(session).get_all()
        return {
            "configured": has_secret(TELEGRAM_BOT_TOKEN),
            "enabled": bool(settings.get("telegram_enabled")),
            "chat_id": settings.get("telegram_chat_id", ""),
        }

    def configure_telegram(self, payload: TelegramConfig, session: Session) -> dict:
        repo = SettingsRepository(session)
        updates = {}
        if payload.bot_token:
            set_secret(TELEGRAM_BOT_TOKEN, payload.bot_token)
        if payload.chat_id is not None:
            updates["telegram_chat_id"] = payload.chat_id
        if payload.enabled is not None:
            updates["telegram_enabled"] = payload.enabled
        if updates:
            repo.update(updates)
        return self.get_telegram_status(session)

    async def send_test_telegram(self, session: Session) -> dict:
        settings = SettingsRepository(session).get_all()
        chat_id = str(settings.get("telegram_chat_id", ""))
        if not chat_id:
            return {"ok": False, "error": "Chat ID not configured"}
        ok, error = await self.telegram.send_message(
            chat_id, "✅ NSE Intraday Scanner test notification successful."
        )
        NotificationRepository(session).log(
            None, "telegram", "sent" if ok else "failed", error
        )
        return {"ok": ok, "error": error}

    async def search_instruments(self, query: str, limit: int = 20) -> list[dict]:
        return await self.instruments.search_api(query, limit)

    def get_snapshot(self) -> dict:
        with session_scope() as session:
            signals = SignalRepository(session).get_latest(20, include_archived=False)
            return {
                "scanner": self.get_scanner_status(),
                "system": self.get_system_status().model_dump(),
                "signals": [
                    {
                        "id": s.id,
                        "symbol": s.symbol,
                        "direction": s.direction,
                        "entry": s.entry,
                        "stop_loss": s.stop_loss,
                        "target_1": s.target_1,
                        "target_2": s.target_2,
                        "target_3": s.target_3,
                        "buy_score": s.buy_score,
                        "sell_score": s.sell_score,
                        "rvol": s.rvol,
                        "htf_direction": s.htf_direction,
                        "universe_source": s.universe_source,
                        "candle_timestamp_utc": s.candle_timestamp_utc.isoformat(),
                        "generated_at_utc": s.generated_at_utc.isoformat(),
                        "archived": s.archived,
                        "is_realtime": s.is_realtime,
                        "quantity": s.quantity,
                        "capital_used": s.capital_used,
                        "outcome": s.outcome,
                    }
                    for s in signals
                ],
                "live_rows": self.get_live_rows(),
                "universe_count": len(self.universe),
            }


app_state = AppState()
