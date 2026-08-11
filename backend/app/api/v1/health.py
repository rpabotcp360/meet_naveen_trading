from datetime import datetime

from fastapi import APIRouter

from app.api.schemas import HealthResponse, SystemStatusResponse
from app.core.config import get_settings
from app.core.timezone import now_utc
from app.services.app_state import app_state

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        timestamp=now_utc(),
        app=get_settings().app_name,
    )


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status() -> SystemStatusResponse:
    return app_state.get_system_status()
