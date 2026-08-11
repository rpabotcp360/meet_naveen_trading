import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Awaitable, Callable

import httpx
import websockets

from app.core.config import get_settings
from app.upstox.auth import UpstoxAuthService
from app.upstox.utils import UPSTOX_V3_BASE

logger = logging.getLogger("upstox")

FeedCallback = Callable[[str, dict], Awaitable[None]]

AUTHORIZE_URL = f"{UPSTOX_V3_BASE}/feed/market-data-feed/authorize"


class UpstoxWebSocketService:
    def __init__(self):
        self.auth = UpstoxAuthService()
        self.settings = get_settings()
        self._ws = None
        self._task: asyncio.Task | None = None
        self._subscribed: set[str] = set()
        self._callback: FeedCallback | None = None
        self._running = False
        self.last_message_at: datetime | None = None
        self.state = "disconnected"

    async def get_feed_url(self) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                AUTHORIZE_URL,
                headers={
                    **self.auth.auth_headers(),
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()["data"]["authorized_redirect_uri"]

    def set_callback(self, callback: FeedCallback) -> None:
        self._callback = callback

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.state = "disconnected"

    async def subscribe(self, instrument_keys: list[str]) -> None:
        new_keys = set(instrument_keys) - self._subscribed
        self._subscribed.update(instrument_keys)
        if self._ws and new_keys:
            await self._send_subscribe(list(new_keys))

    async def unsubscribe(self, instrument_keys: list[str]) -> None:
        for key in instrument_keys:
            self._subscribed.discard(key)
        if self._ws and instrument_keys:
            await self._send_unsubscribe(instrument_keys)

    async def _send_subscribe(self, keys: list[str]) -> None:
        if not self._ws:
            return
        msg = {
            "guid": str(uuid.uuid4()),
            "method": "sub",
            "data": {"mode": "ltpc", "instrumentKeys": keys},
        }
        await self._ws.send(json.dumps(msg).encode("utf-8"))

    async def _send_unsubscribe(self, keys: list[str]) -> None:
        if not self._ws:
            return
        msg = {
            "guid": str(uuid.uuid4()),
            "method": "unsub",
            "data": {"instrumentKeys": keys},
        }
        await self._ws.send(json.dumps(msg).encode("utf-8"))

    async def _run_loop(self) -> None:
        backoff = 1
        while self._running:
            try:
                url = await self.get_feed_url()
                self.state = "connecting"
                async with websockets.connect(url, ping_interval=20) as ws:
                    self._ws = ws
                    self.state = "connected"
                    backoff = 1
                    if self._subscribed:
                        await self._send_subscribe(list(self._subscribed))
                    async for message in ws:
                        self.last_message_at = datetime.utcnow()
                        await self._handle_message(message)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Upstox WS error: %s", exc)
                self.state = "reconnecting"
                await asyncio.sleep(min(backoff, 30))
                backoff *= 2
        self.state = "disconnected"

    async def _handle_message(self, message) -> None:
        if not self._callback:
            return

        ticks: list[tuple[str, dict]] = []
        if isinstance(message, bytes):
            from app.upstox.protobuf_decoder import decode_feed_message

            ticks = decode_feed_message(message)
        else:
            try:
                parsed = json.loads(message)
            except json.JSONDecodeError:
                return
            if isinstance(parsed, dict) and parsed.get("feeds"):
                for key, feed in parsed["feeds"].items():
                    ltpc = feed.get("ltpc", {})
                    ticks.append(
                        (
                            key,
                            {
                                "instrument_key": key,
                                "ltp": float(ltpc.get("ltp", 0)),
                                "volume": float(ltpc.get("ltq", 0)),
                                "close": float(ltpc.get("cp", 0)),
                            },
                        )
                    )

        for instrument_key, tick in ticks:
            if instrument_key and tick.get("ltp", 0) > 0:
                await self._callback(instrument_key, tick)

    def is_stale(self) -> bool:
        if not self.last_message_at:
            return True
        elapsed = (datetime.utcnow() - self.last_message_at).total_seconds()
        return elapsed > self.settings.stale_feed_threshold_seconds
