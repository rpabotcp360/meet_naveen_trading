import json
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.upstox.auth import UpstoxAuthService
from app.upstox.utils import is_valid_instrument_key

INSTRUMENTS_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
)


class UpstoxInstrumentService:
    def __init__(self):
        self.settings = get_settings()
        self.auth = UpstoxAuthService()
        self._cache: list[dict] | None = None

    @property
    def cache_path(self) -> Path:
        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.settings.cache_dir / "nse_instruments.json"

    async def load_instruments(self, force: bool = False) -> list[dict]:
        if self._cache and not force:
            return self._cache
        if self.cache_path.exists() and not force:
            self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return self._cache
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(INSTRUMENTS_URL, follow_redirects=True)
            resp.raise_for_status()
            import gzip

            data = gzip.decompress(resp.content)
            instruments = json.loads(data)
        equities = [
            i
            for i in instruments
            if i.get("segment") == "NSE_EQ"
            and i.get("instrument_type") == "EQ"
        ]
        self.cache_path.write_text(json.dumps(equities), encoding="utf-8")
        self._cache = equities
        return equities

    async def search(self, query: str, limit: int = 20) -> list[dict]:
        instruments = await self.load_instruments()
        q = query.upper().strip()
        results = []
        for inst in instruments:
            symbol = inst.get("trading_symbol") or inst.get("tradingsymbol", "")
            name = inst.get("name", "")
            if q in symbol.upper() or q in name.upper():
                results.append(
                    {
                        "instrument_key": inst.get("instrument_key", ""),
                        "trading_symbol": symbol,
                        "name": name,
                        "exchange": "NSE",
                    }
                )
            if len(results) >= limit:
                break
        return results

    async def get_by_trading_symbol(self, trading_symbol: str) -> dict | None:
        instruments = await self.load_instruments()
        symbol = trading_symbol.upper().strip()
        for inst in instruments:
            ts = inst.get("trading_symbol") or inst.get("tradingsymbol", "")
            if ts.upper() == symbol:
                return inst
        return None

    async def get_by_key(self, instrument_key: str) -> dict | None:
        instruments = await self.load_instruments()
        for inst in instruments:
            if inst.get("instrument_key") == instrument_key:
                return inst
        return None

    async def resolve_instrument_key(
        self, instrument_key: str, trading_symbol: str = ""
    ) -> str:
        if is_valid_instrument_key(instrument_key):
            return instrument_key
        symbol = trading_symbol or instrument_key.split("|")[-1]
        inst = await self.get_by_trading_symbol(symbol)
        if inst:
            return inst.get("instrument_key", instrument_key)
        return instrument_key

    async def search_api(self, query: str, limit: int = 20) -> list[dict]:
        if not self.auth.is_authenticated():
            return await self.search(query, limit)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.upstox.com/v2/search/instruments",
                params={"query": query},
                headers=self.auth.auth_headers(),
            )
            if resp.status_code != 200:
                return await self.search(query, limit)
            data = resp.json().get("data", [])
            return [
                {
                    "instrument_key": i.get("instrument_key", ""),
                    "trading_symbol": i.get(
                        "tradingsymbol", i.get("trading_symbol", "")
                    ),
                    "name": i.get("name", ""),
                    "exchange": i.get("exchange", "NSE"),
                }
                for i in data[:limit]
            ]
