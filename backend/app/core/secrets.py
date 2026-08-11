"""Secrets via OS keyring, with a locked file fallback for headless Linux."""

from __future__ import annotations

import json
import os
from pathlib import Path

import keyring
from keyring.backends.fail import Keyring as FailKeyring
from keyring.errors import KeyringError, NoKeyringError, PasswordDeleteError

from app.core.config import ROOT_DIR

SERVICE_NAME = "nse-intraday-scanner"

UPSTOX_ACCESS_TOKEN = "upstox_access_token"
UPSTOX_CLIENT_SECRET = "upstox_client_secret"
TELEGRAM_BOT_TOKEN = "telegram_bot_token"
AUTH_USERNAME = "auth_username"
AUTH_PASSWORD_HASH = "auth_password_hash"

_FALLBACK_PATH = ROOT_DIR / "data" / ".secrets.json"


def _keyring_unavailable() -> bool:
    return isinstance(keyring.get_keyring(), FailKeyring)


def _load_fallback() -> dict[str, str]:
    if not _FALLBACK_PATH.exists():
        return {}
    try:
        data = json.loads(_FALLBACK_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _save_fallback(data: dict[str, str]) -> None:
    _FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _FALLBACK_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(_FALLBACK_PATH)
    try:
        os.chmod(_FALLBACK_PATH, 0o600)
    except OSError:
        pass


def set_secret(key: str, value: str) -> None:
    if not _keyring_unavailable():
        try:
            keyring.set_password(SERVICE_NAME, key, value)
            return
        except (NoKeyringError, KeyringError):
            pass
    data = _load_fallback()
    data[key] = value
    _save_fallback(data)


def get_secret(key: str) -> str | None:
    if not _keyring_unavailable():
        try:
            return keyring.get_password(SERVICE_NAME, key)
        except (NoKeyringError, KeyringError):
            pass
    return _load_fallback().get(key)


def delete_secret(key: str) -> None:
    if not _keyring_unavailable():
        try:
            keyring.delete_password(SERVICE_NAME, key)
            return
        except PasswordDeleteError:
            return
        except (NoKeyringError, KeyringError):
            pass
    data = _load_fallback()
    if key in data:
        del data[key]
        _save_fallback(data)


def has_secret(key: str) -> bool:
    return get_secret(key) is not None
