from urllib.parse import quote


UPSTOX_V3_BASE = "https://api.upstox.com/v3"


def encode_key_for_path(instrument_key: str) -> str:
    """Encode instrument key once for URL path segments."""
    return quote(instrument_key, safe="")


def join_keys_for_query(instrument_keys: list[str]) -> str:
    """Comma-separated keys for query params; let httpx encode once."""
    return ",".join(instrument_keys)


def is_valid_instrument_key(instrument_key: str) -> bool:
    if "|" not in instrument_key:
        return False
    suffix = instrument_key.split("|", 1)[1]
    return suffix.startswith("INE") or suffix.startswith("INF")


def normalize_quote_response(data: dict) -> dict:
    """Map v3 quote payloads keyed by symbol back to instrument_token keys."""
    normalized: dict = {}
    for key, entry in data.items():
        if not isinstance(entry, dict):
            continue
        token = entry.get("instrument_token") or key
        normalized[token] = entry
    return normalized
