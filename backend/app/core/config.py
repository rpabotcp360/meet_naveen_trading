from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NSE Intraday Scanner"
    app_env: str = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'scanner.db'}"
    log_level: str = "INFO"
    log_dir: str = str(ROOT_DIR / "logs")

    upstox_api_key: str = ""
    upstox_redirect_uri: str = "http://127.0.0.1:8000/api/v1/upstox/callback"

    # Bootstrap dashboard login on first start (stored in keyring / data/.secrets.json)
    auth_username: str = ""
    auth_password: str = ""

    default_capital_per_trade: float = 20000.0
    default_strategy_mode: str = "balanced"
    default_top_n: int = 30
    stale_feed_threshold_seconds: int = 30

    market_timezone: str = "Asia/Kolkata"

    @property
    def data_dir(self) -> Path:
        return ROOT_DIR / "data"

    @property
    def cache_dir(self) -> Path:
        return ROOT_DIR / "backend" / "cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()
