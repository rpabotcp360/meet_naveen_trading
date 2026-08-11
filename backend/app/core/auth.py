"""Single-user local auth. Credentials live only in the OS keyring (same
mechanism already used for the Upstox/Telegram tokens) — never in a source
file or in plaintext in the database. Sessions are persisted in SQLite so a
backend restart during development doesn't force a re-login every time."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.core.secrets import AUTH_PASSWORD_HASH, AUTH_USERNAME, get_secret, set_secret
from app.storage.models import AuthSession

SESSION_TTL = timedelta(days=7)
PBKDF2_ITERATIONS = 200_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, _ = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hash_password(password, bytes.fromhex(salt_hex))
    return secrets.compare_digest(candidate, stored)


def set_credentials(username: str, password: str) -> None:
    set_secret(AUTH_USERNAME, username)
    set_secret(AUTH_PASSWORD_HASH, hash_password(password))


def credentials_configured() -> bool:
    return bool(get_secret(AUTH_USERNAME) and get_secret(AUTH_PASSWORD_HASH))


def verify_credentials(username: str, password: str) -> bool:
    stored_username = get_secret(AUTH_USERNAME)
    stored_hash = get_secret(AUTH_PASSWORD_HASH)
    if not stored_username or not stored_hash:
        return False
    # Compare usernames with constant-time equality too — this is a
    # single-user login, so the username is effectively part of the secret.
    if not secrets.compare_digest(username, stored_username):
        return False
    return verify_password(password, stored_hash)


def create_session(session: Session, username: str) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + SESSION_TTL
    session.add(AuthSession(token=token, username=username, expires_at=expires_at))
    session.commit()
    return token, expires_at


def get_valid_session(session: Session, token: str) -> AuthSession | None:
    record = session.get(AuthSession, token)
    if not record:
        return None
    if record.expires_at < datetime.utcnow():
        session.delete(record)
        session.commit()
        return None
    return record


def delete_session(session: Session, token: str) -> None:
    record = session.get(AuthSession, token)
    if record:
        session.delete(record)
        session.commit()


def purge_expired_sessions(session: Session) -> None:
    now = datetime.utcnow()
    stmt = select(AuthSession).where(AuthSession.expires_at < now)
    for record in session.exec(stmt).all():
        session.delete(record)
    session.commit()
