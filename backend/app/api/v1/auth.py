from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from app.api.schemas import LoginRequest, LoginResponse, SignupResponse
from app.core.auth import (
    create_session,
    create_user,
    credentials_configured,
    delete_session,
    get_user,
    get_valid_session,
    verify_password,
)
from app.storage.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
def auth_status():
    return {"configured": credentials_configured()}


@router.post("/signup", response_model=SignupResponse)
def signup(payload: LoginRequest, session: Session = Depends(get_db)):
    if credentials_configured():
        raise HTTPException(
            status_code=403,
            detail="Signup closed — an account already exists. Please sign in.",
        )
    username = payload.username.strip()
    password = payload.password
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    create_user(session, username, password)
    return SignupResponse(ok=True, username=username, message="Account created. Please sign in.")


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)):
    username = payload.username.strip()
    password = payload.password
    if not credentials_configured():
        raise HTTPException(
            status_code=404,
            detail="No account yet — please sign up first",
        )
    user = get_user(session, username)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token, expires_at = create_session(session, username)
    return LoginResponse(token=token, username=username, expires_at=expires_at)


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
