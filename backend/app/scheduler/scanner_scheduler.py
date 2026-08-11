import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.timezone import IST, ist_date

logger = logging.getLogger("scanner")

WEEKDAYS = "mon-fri"

# How long to wait after auto-start before concluding "no data means holiday".
# NSE pre-open starts 09:00 and the first real ticks land by ~09:15-09:20 on
# any trading day, so 25 minutes is generous room before treating silence as
# a holiday rather than a slow start.
ACTIVITY_CHECK_HOUR = 9
ACTIVITY_CHECK_MINUTE = 25


class ScannerScheduler:
    def __init__(self, app_state):
        self.app_state = app_state
        self.scheduler = AsyncIOScheduler(timezone=IST)
        self.started = False
        self.next_auto_start: object = None
        self.next_auto_stop: object = None

    def start(self) -> None:
        if self.started:
            return
        self.scheduler.add_job(
            self._auto_start,
            CronTrigger(hour=9, minute=0, day_of_week=WEEKDAYS, timezone=IST),
            id="auto_start",
        )
        self.scheduler.add_job(
            self._check_market_activity,
            CronTrigger(
                hour=ACTIVITY_CHECK_HOUR,
                minute=ACTIVITY_CHECK_MINUTE,
                day_of_week=WEEKDAYS,
                timezone=IST,
            ),
            id="activity_check",
        )
        self.scheduler.add_job(
            self._stop_new_signals,
            CronTrigger(hour=14, minute=45, day_of_week=WEEKDAYS, timezone=IST),
            id="stop_signals",
        )
        self.scheduler.add_job(
            self._auto_stop,
            CronTrigger(hour=15, minute=45, day_of_week=WEEKDAYS, timezone=IST),
            id="auto_stop",
        )
        self.scheduler.start()
        self.started = True
        self._refresh_next_run_times()

    def _refresh_next_run_times(self) -> None:
        start_job = self.scheduler.get_job("auto_start")
        stop_job = self.scheduler.get_job("auto_stop")
        self.next_auto_start = getattr(start_job, "next_run_time", None)
        self.next_auto_stop = getattr(stop_job, "next_run_time", None)

    def get_auto_mode_status(self) -> dict:
        return {
            "enabled": self.started,
            "next_start": self.next_auto_start.isoformat() if self.next_auto_start else None,
            "next_stop": self.next_auto_stop.isoformat() if self.next_auto_stop else None,
        }

    async def _is_market_likely_open_today(self) -> bool:
        """Best-effort holiday check: Upstox's market-status endpoint only
        stamps `last_updated` when the exchange actually opens a new
        session. If that stamp isn't from today, either the exchange hasn't
        published anything (holiday) or the check itself failed — in the
        latter case we fail open so a transient API hiccup never blocks a
        real trading day."""
        try:
            status = await self.app_state.market_status.get_status("NSE")
        except Exception:
            logger.warning("Market status check failed; proceeding with auto-start anyway")
            return True

        if not isinstance(status, dict) or not status.get("status"):
            logger.warning("Market status unavailable; proceeding with auto-start anyway")
            return True

        last_updated = status.get("last_updated")
        if not last_updated:
            return True

        try:
            updated_date = datetime.fromtimestamp(int(last_updated) / 1000, tz=IST).date()
        except Exception:
            return True

        if updated_date != ist_date():
            logger.info(
                "Market status last updated %s (not today) — likely a holiday, skipping auto-start",
                updated_date,
            )
            return False
        return True

    async def _auto_start(self) -> None:
        self._refresh_next_run_times()
        if not self.app_state.auth.is_authenticated():
            logger.info("Auto-start skipped — Upstox not authenticated yet")
            return
        if not await self._is_market_likely_open_today():
            self.app_state.last_error = "Auto-start skipped — market appears closed today (holiday?)"
            return
        logger.info("Auto-starting scanner at 09:00 IST")
        try:
            await self.app_state.start_scanner()
        except Exception:
            logger.exception("Auto-start failed")

    async def _check_market_activity(self) -> None:
        """Holiday safety net: if we auto-started but nothing has actually
        traded by 09:25, the exchange almost certainly isn't open today —
        stop and let tomorrow's auto-start try again instead of sitting
        idle in a 'running' state that never produces signals."""
        if self.app_state.scanner_state != "running":
            return
        no_ticks = self.app_state.upstox_ws.last_message_at is None
        no_candles = self.app_state.market_engine.last_5m_candle_at is None
        if no_ticks and no_candles:
            logger.warning("No market activity by 09:25 IST — likely a holiday, stopping scanner")
            self.app_state.last_error = "Stopped — no market activity detected (holiday?)"
            await self.app_state.stop_scanner()

    async def _stop_new_signals(self) -> None:
        logger.info("Stop new signals at 14:45 IST")
        self.app_state.allow_new_signals = False

    async def _auto_stop(self) -> None:
        self._refresh_next_run_times()
        logger.info("Auto-stopping scanner at 15:45 IST")
        await self.app_state.stop_scanner()
        self.app_state.allow_new_signals = True

    def shutdown(self) -> None:
        if self.started:
            self.scheduler.shutdown(wait=False)
