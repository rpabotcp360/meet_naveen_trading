import httpx

from app.upstox.auth import UpstoxAuthService
from app.upstox.utils import UPSTOX_V3_BASE, encode_key_for_path


class UpstoxHistoricalService:
    def __init__(self):
        self.auth = UpstoxAuthService()

    async def get_candles(
        self,
        instrument_key: str,
        unit: str,
        interval: int,
        from_date: str,
        to_date: str,
    ) -> list[list]:
        encoded_key = encode_key_for_path(instrument_key)
        url = (
            f"{UPSTOX_V3_BASE}/historical-candle/{encoded_key}/"
            f"{unit}/{interval}/{to_date}/{from_date}"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, headers=self.auth.auth_headers())
            if resp.status_code != 200:
                return []
            return resp.json().get("data", {}).get("candles", [])

    async def get_intraday_candles(
        self, instrument_key: str, unit: str, interval: int
    ) -> list[list]:
        encoded_key = encode_key_for_path(instrument_key)
        url = (
            f"{UPSTOX_V3_BASE}/historical-candle/intraday/"
            f"{encoded_key}/{unit}/{interval}"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, headers=self.auth.auth_headers())
            if resp.status_code != 200:
                return []
            return resp.json().get("data", {}).get("candles", [])
