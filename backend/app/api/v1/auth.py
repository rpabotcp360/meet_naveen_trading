from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from app.api.schemas import LoginRequest, LoginResponse
from app.core.auth import (
    create_session,
    credentials_configured,
    delete_session,
    get_valid_session,
    set_credentials,
    verify_credentials,
)
from app.storage.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
def auth_status():
    return {"configured": credentials_configured()}


@router.post("/setup", response_model=LoginResponse)
def setup(payload: LoginRequest, session: Session = Depends(get_db)):
    """Create the single admin account on a fresh install. Disabled once set."""
    if credentials_configured():
        raise HTTPException(status_code=409, detail="Credentials already configured")
    username = payload.username.strip()
    password = payload.password
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    set_credentials(username, password)
    token, expires_at = create_session(session, username)
    return LoginResponse(token=token, username=username, expires_at=expires_at)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)):
    if not credentials_configured():
        raise HTTPException(
            status_code=401,
            detail="No login configured yet — create an account on this page first",
        )
    if not verify_credentials(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token, expires_at = create_session(session, payload.username)
    return LoginResponse(token=token, username=payload.username, expires_at=expires_at)


@router.post("/logout")
def logout(authorization: str | None = Header(default=None), session: Session = Depends(get_db)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token:
        delete_session(session, token)
    return {"ok": True}


@router.get("/me")
def me(authorization: str | None = Header(default=None), session: Session = Depends(get_db)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    record = get_valid_session(session, token) if token else None
    if not record:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"username": record.username, "expires_at": record.expires_at}
