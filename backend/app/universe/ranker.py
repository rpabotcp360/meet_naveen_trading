import logging
from dataclasses import dataclass

from app.universe.base_universe import BASE_UNIVERSE
from app.upstox.instruments import UpstoxInstrumentService
from app.upstox.market_snapshot import UpstoxMarketSnapshotService

logger = logging.getLogger("scanner")

RANK_WEIGHTS = {
    "rvol": 0.30,
    "volume": 0.25,
    "movement": 0.20,
    "atr": 0.15,
    "trend": 0.10,
}


@dataclass
class RankedSymbol:
    instrument_key: str
    symbol: str
    company_name: str
    rank: int
    rank_score: float
    source: str = "TOP30"


class UniverseRanker:
    def __init__(self):
        self.instruments = UpstoxInstrumentService()
        self.snapshot = UpstoxMarketSnapshotService()

    async def resolve_base_universe(self) -> list[dict]:
        all_instruments = await self.instruments.load_instruments()
        symbol_map = {i["trading_symbol"]: i for i in all_instruments}
        resolved = []
        for symbol in BASE_UNIVERSE:
            inst = symbol_map.get(symbol)
            if inst:
                resolved.append(
                    {
                        "instrument_key": inst["instrument_key"],
                        "trading_symbol": symbol,
                        "company_name": inst.get("name", symbol),
                    }
                )
        return resolved

    async def rank_top_n(self, top_n: int = 30) -> list[RankedSymbol]:
        base = await self.resolve_base_universe()
        keys = [b["instrument_key"] for b in base]
        ltp_data = await self.snapshot.get_ltp(keys)
        ohlc_data = await self.snapshot.get_ohlc(keys)

        scored = []
        for item in base:
            key = item["instrument_key"]
            ltp_entry = ltp_data.get(key, {})
            ohlc_entry = ohlc_data.get(key, {})
            ltp = float(ltp_entry.get("last_price", ltp_entry.get("ltp", 0)))
            prev_close = float(
                ltp_entry.get("cp")
                or (ohlc_entry.get("prev_ohlc") or {}).get("close")
                or (ohlc_entry.get("live_ohlc") or {}).get("close")
                or ltp
            )
            volume = float(ltp_entry.get("volume", 0))
            if ltp <= 0:
                continue
            movement = abs((ltp - prev_close) / prev_close * 100) if prev_close else 0
            rvol_proxy = min(volume / 1_000_000, 5.0) if volume else 0
            score = (
                rvol_proxy * RANK_WEIGHTS["rvol"]
                + min(volume / 5_000_000, 1) * RANK_WEIGHTS["volume"]
                + min(movement / 5, 1) * RANK_WEIGHTS["movement"]
                + 0.5 * RANK_WEIGHTS["atr"]
                + (0.5 if ltp > prev_close else 0.2) * RANK_WEIGHTS["trend"]
            )
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        result = []
        for rank, (score, item) in enumerate(scored[:top_n], start=1):
            result.append(
                RankedSymbol(
                    instrument_key=item["instrument_key"],
                    symbol=item["trading_symbol"],
                    company_name=item["company_name"],
                    rank=rank,
                    rank_score=round(score, 4),
                )
            )

        if not result and base:
            logger.warning("LTP snapshot empty; using base universe fallback")
            for rank, item in enumerate(base[:top_n], start=1):
                result.append(
                    RankedSymbol(
                        instrument_key=item["instrument_key"],
                        symbol=item["trading_symbol"],
                        company_name=item["company_name"],
                        rank=rank,
                        rank_score=0.0,
                    )
                )
        return result

    async def merge_with_watchlist(
        self,
        top30: list[RankedSymbol],
        watchlist: list,
    ) -> list[dict]:
        merged: dict[str, dict] = {}
        top_keys = {t.instrument_key for t in top30}

        for t in top30:
            merged[t.instrument_key] = {
                "instrument_key": t.instrument_key,
                "trading_symbol": t.symbol,
                "company_name": t.company_name,
                "rank": t.rank,
                "rank_score": t.rank_score,
                "source": "TOP30",
            }

        for item in watchlist:
            if not item.enabled:
                continue
            key = item.instrument_key
            if key in merged:
                merged[key]["source"] = "BOTH"
            else:
                merged[key] = {
                    "instrument_key": key,
                    "trading_symbol": item.trading_symbol,
                    "company_name": item.company_name,
                    "rank": 0,
                    "rank_score": 0,
                    "source": "WATCHLIST",
                }

        return list(merged.values())
