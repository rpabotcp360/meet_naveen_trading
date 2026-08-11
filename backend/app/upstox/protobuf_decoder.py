"""Decode Upstox Market Data Feed V3 protobuf messages."""

from __future__ import annotations

import logging

logger = logging.getLogger("upstox")


def decode_feed_message(data: bytes) -> list[tuple[str, dict]]:
    try:
        from app.upstox import MarketDataFeed_pb2

        response = MarketDataFeed_pb2.FeedResponse()
        response.ParseFromString(data)
        ticks: list[tuple[str, dict]] = []
        for instrument_key, feed in response.feeds.items():
            if feed.HasField("ltpc"):
                ltpc = feed.ltpc
                ticks.append(
                    (
                        instrument_key,
                        {
                            "instrument_key": instrument_key,
                            "ltp": float(ltpc.ltp),
                            "volume": float(ltpc.ltq),
                            "close": float(ltpc.cp),
                        },
                    )
                )
            elif feed.HasField("fullFeed") and feed.fullFeed.HasField("marketFF"):
                ltpc = feed.fullFeed.marketFF.ltpc
                ticks.append(
                    (
                        instrument_key,
                        {
                            "instrument_key": instrument_key,
                            "ltp": float(ltpc.ltp),
                            "volume": float(feed.fullFeed.marketFF.vtt),
                            "close": float(ltpc.cp),
                        },
                    )
                )
        return ticks
    except Exception as exc:
        logger.debug("Protobuf decode failed: %s", exc)
        return []
