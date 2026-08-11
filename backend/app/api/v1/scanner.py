from fastapi import APIRouter, HTTPException

from app.services.app_state import app_state

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/status")
def scanner_status():
    return app_state.get_scanner_status()


@router.post("/start")
async def start_scanner():
    try:
        await app_state.start_scanner()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return app_state.get_scanner_status()


@router.post("/stop")
async def stop_scanner():
    await app_state.stop_scanner()
    return app_state.get_scanner_status()


@router.get("/universe")
def scanner_universe():
    return app_state.get_universe()


@router.post("/universe/refresh")
async def refresh_universe():
    await app_state.refresh_universe()
    return app_state.get_universe()


@router.get("/live")
def scanner_live():
    return app_state.get_live_rows()
