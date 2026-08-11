import asyncio
import logging

import httpx

from app.core.secrets import TELEGRAM_BOT_TOKEN, get_secret
from app.core.timezone import to_ist
from app.storage.repositories import NotificationRepository

logger = logging.getLogger("telegram")

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramNotifier:
    def __init__(self):
        self._retry_delays = [1, 2, 5, 10, 30]

    async def send_message(self, chat_id: str, text: str) -> tuple[bool, str]:
        token = get_secret(TELEGRAM_BOT_TOKEN)
        if not token:
            return False, "Bot token not configured"
        url = f"{TELEGRAM_API_BASE.format(token=token)}/sendMessage"
        last_error = ""
        for delay in self._retry_delays:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        url,
                        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                    )
                    if resp.status_code == 200:
                        return True, ""
                    last_error = resp.text[:200]
            except Exception as exc:
                last_error = str(exc)
            await asyncio.sleep(delay)
        return False, last_error

    async def send_photo(self, chat_id: str, photo_bytes: bytes, caption: str = "") -> tuple[bool, str]:
        token = get_secret(TELEGRAM_BOT_TOKEN)
        if not token:
            return False, "Bot token not configured"
        url = f"{TELEGRAM_API_BASE.format(token=token)}/sendPhoto"
        last_error = ""
        for delay in self._retry_delays:
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.post(
                        url,
                        data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                        files={"photo": ("signal.png", photo_bytes, "image/png")},
                    )
                    if resp.status_code == 200:
                        return True, ""
                    last_error = resp.text[:200]
            except Exception as exc:
                last_error = str(exc)
            await asyncio.sleep(delay)
        return False, last_error

    def format_signal(self, signal) -> str:
        emoji = "🟢" if signal.direction == "BUY" else "🔴"
        alert_type = "⏱ Past Alert (found on catch-up scan)" if not signal.is_realtime else "🔴 Live Alert"
        candle_start = to_ist(signal.candle_timestamp_utc)
        candle_end = to_ist(signal.generated_at_utc)
        triggered = (
            f"{candle_start.strftime('%d %b %Y')}, "
            f"{candle_start.strftime('%H:%M')}–{candle_end.strftime('%H:%M')} IST"
        )
        return (
            f"{emoji} <b>{signal.direction} SIGNAL</b>\n\n"
            f"Stock: {signal.symbol}\n"
            f"Triggered: {triggered} (5m candle)\n"
            f"Type: {alert_type}\n"
            f"Entry: ₹{signal.entry:.2f}\n"
            f"Qty for ₹{signal.capital_used:.0f}: {signal.quantity}\n"
            f"Stop Loss: ₹{signal.stop_loss:.2f}\n"
            f"T1: ₹{signal.target_1:.2f}\n"
            f"T2: ₹{signal.target_2:.2f}\n"
            f"T3: ₹{signal.target_3:.2f}\n"
            f"{signal.direction} Score: {signal.buy_score if signal.direction == 'BUY' else signal.sell_score}/100\n"
            f"Mode: {signal.mode.title()}\n"
            f"Timeframe: 5m\n"
            f"RVOL: {signal.rvol:.2f}x\n"
            f"Trend: {signal.supertrend_direction}\n"
            f"VWAP: {'Above' if signal.direction == 'BUY' else 'Below'}\n"
            f"HTF: {signal.htf_direction}\n"
            f"Source: {signal.universe_source}"
        )

    def format_caption(self, signal) -> str:
        emoji = "🟢" if signal.direction == "BUY" else "🔴"
        return (
            f"{emoji} <b>{signal.direction} {signal.symbol}</b> · "
            f"Entry ₹{signal.entry:.2f} · Score {signal.buy_score}/100"
        )

    async def notify_signal(
        self, signal, chat_id: str, session, signal_repo
    ) -> bool:
        notifier_repo = NotificationRepository(session)

        try:
            from app.notifications.signal_image import render_signal_card

            image_bytes = render_signal_card(signal)
            ok, error = await self.send_photo(chat_id, image_bytes, self.format_caption(signal))
        except Exception:
            logger.exception("Signal image render failed — falling back to text notification")
            ok, error = False, "image render failed"

        if not ok:
            # Card image failed to render or send — a plain-text alert still
            # beats no alert at all.
            ok, error = await self.send_message(chat_id, self.format_signal(signal))

        notifier_repo.log(
            signal_id=signal.id,
            channel="telegram",
            status="sent" if ok else "failed",
            error_message=error,
        )
        if ok:
            notifier_repo.mark_signal_sent(signal)
        return ok
