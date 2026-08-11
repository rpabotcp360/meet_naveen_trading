import httpx

from app.upstox.auth import UpstoxAuthService
from app.upstox.utils import UPSTOX_V3_BASE, join_keys_for_query, normalize_quote_response

BATCH_SIZE = 80


class UpstoxMarketSnapshotService:
    def __init__(self):
        self.auth = UpstoxAuthService()

    async def _get(self, path: str, params: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{UPSTOX_V3_BASE}{path}",
                params=params,
                headers=self.auth.auth_headers(),
            )
            if resp.status_code != 200:
                return {}
            return resp.json().get("data", {})

    async def get_ltp(self, instrument_keys: list[str]) -> dict:
        if not instrument_keys:
            return {}
        merged: dict = {}
        for i in range(0, len(instrument_keys), BATCH_SIZE):
            batch = instrument_keys[i : i + BATCH_SIZE]
            data = await self._get(
                "/market-quote/ltp",
                {"instrument_key": join_keys_for_query(batch)},
            )
            merged.update(normalize_quote_response(data))
        return merged

    async def get_ohlc(self, instrument_keys: list[str]) -> dict:
        if not instrument_keys:
            return {}
        merged: dict = {}
        for i in range(0, len(instrument_keys), BATCH_SIZE):
            batch = instrument_keys[i : i + BATCH_SIZE]
            data = await self._get(
                "/market-quote/ohlc",
                {"instrument_key": join_keys_for_query(batch), "interval": "1d"},
            )
            merged.update(normalize_quote_response(data))
        return merged
