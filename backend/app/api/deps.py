from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from app.core.auth import get_valid_session
from app.storage.database import get_db
from app.storage.models import AuthSession


def require_auth(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_db),
) -> AuthSession:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    record = get_valid_session(session, token)
    if not record:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return record
