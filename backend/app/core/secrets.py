import keyring

SERVICE_NAME = "nse-intraday-scanner"

UPSTOX_ACCESS_TOKEN = "upstox_access_token"
UPSTOX_CLIENT_SECRET = "upstox_client_secret"
TELEGRAM_BOT_TOKEN = "telegram_bot_token"
AUTH_USERNAME = "auth_username"
AUTH_PASSWORD_HASH = "auth_password_hash"


def set_secret(key: str, value: str) -> None:
    keyring.set_password(SERVICE_NAME, key, value)


def get_secret(key: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, key)


def delete_secret(key: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, key)
    except keyring.errors.PasswordDeleteError:
        pass


def has_secret(key: str) -> bool:
    return get_secret(key) is not None
