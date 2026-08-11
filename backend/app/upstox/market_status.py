import httpx

from app.upstox.auth import UpstoxAuthService

UPSTOX_BASE = "https://api.upstox.com/v2"


class UpstoxMarketStatusService:
    def __init__(self):
        self.auth = UpstoxAuthService()

    async def get_status(self, exchange: str = "NSE") -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{UPSTOX_BASE}/market/status/{exchange}",
                headers=self.auth.auth_headers(),
            )
            if resp.status_code != 200:
                return {"market_status": "unknown"}
            return resp.json().get("data", {})
