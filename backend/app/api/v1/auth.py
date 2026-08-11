from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from app.api.schemas import LoginRequest, LoginResponse
from app.core.auth import create_session, delete_session, get_valid_session, verify_credentials
from app.storage.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)):
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
