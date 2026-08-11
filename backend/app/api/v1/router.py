from fastapi import APIRouter, Depends

from app.api.deps import require_auth
from app.api.v1 import auth, health, scanner, segments, settings, signals, telegram, upstox, watchlist

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)

# Everything below requires a valid session — health and auth/login are the
# only endpoints reachable without one.
protected_dep = [Depends(require_auth)]
api_router.include_router(settings.router, dependencies=protected_dep)
api_router.include_router(scanner.router, dependencies=protected_dep)
api_router.include_router(signals.router, dependencies=protected_dep)
api_router.include_router(watchlist.router, dependencies=protected_dep)
api_router.include_router(segments.router, dependencies=protected_dep)
api_router.include_router(upstox.router, dependencies=protected_dep)
api_router.include_router(telegram.router, dependencies=protected_dep)
