"""Dashboard auth: users in SQLite, sessions in SQLite."""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.storage.models import AuthSession, AuthUser

SESSION_TTL = timedelta(days=7)
PBKDF2_ITERATIONS = 200_000
logger = logging.getLogger(__name__)


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


def get_user(session: Session, username: str) -> AuthUser | None:
    return session.exec(select(AuthUser).where(AuthUser.username == username)).first()


def user_exists(session: Session, username: str) -> bool:
    return get_user(session, username) is not None


def create_user(session: Session, username: str, password: str) -> AuthUser:
    user = AuthUser(username=username, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def verify_credentials(session: Session, username: str, password: str) -> AuthUser | None:
    user = get_user(session, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


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


def migrate_legacy_keyring_user(session: Session) -> None:
    """One-time: move old single-user keyring credentials into auth_users."""
    if session.exec(select(AuthUser).limit(1)).first():
        return
    try:
        from app.core.secrets import AUTH_PASSWORD_HASH, AUTH_USERNAME, get_secret

        username = (get_secret(AUTH_USERNAME) or "").strip()
        password_hash = get_secret(AUTH_PASSWORD_HASH)
        if username and password_hash:
            session.add(AuthUser(username=username, password_hash=password_hash))
            session.commit()
            logger.info("Migrated legacy keyring login user %s into auth_users", username)
    except Exception:
        logger.exception("Legacy keyring auth migration skipped")


# Back-compat helpers used by env bootstrap / older tests
def set_credentials(username: str, password: str) -> None:
    from app.storage.database import session_scope

    with session_scope() as session:
        existing = get_user(session, username)
        if existing:
            existing.password_hash = hash_password(password)
            session.add(existing)
            session.commit()
        else:
            create_user(session, username, password)


def credentials_configured() -> bool:
    from app.storage.database import session_scope

    with session_scope() as session:
        return session.exec(select(AuthUser).limit(1)).first() is not None
