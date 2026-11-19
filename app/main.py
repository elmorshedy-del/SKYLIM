"""Application factory.

    uvicorn app.main:app --host 0.0.0.0 --port $PORT

On startup it applies pending migrations (AUTO_MIGRATE, default on) and starts a
light background loop: release lapsed payment holds, deliver queued email and
purge finished-trip locations.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .config import get_settings
from .domain.status import TransitionError
from .errors import AppError
from .services import bookings, notifications, tracking
from .web import admin, integrations, public_api, site, trips

log = logging.getLogger("meridian")
SWEEP_SECONDS = 60

CSP = ("default-src 'self'; "
       "script-src 'self' 'unsafe-inline' https://unpkg.com; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
       "font-src 'self' https://fonts.gstatic.com; "
       "img-src 'self' data: https:; "
       "connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


def sweep_once(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    s = get_settings()
    with db.tx() as conn:
        bookings.release_expired_holds(conn, now)
        tracking.purge(conn, now, s.tracking_retention_hours)
    notifications.deliver_pending(db.tx)


async def _sweeper() -> None:
    while True:
        try:
            await asyncio.to_thread(sweep_once)
        except Exception:  # keep the loop alive; the next tick retries
            log.exception("background sweep failed")
        await asyncio.sleep(SWEEP_SECONDS)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("AUTO_MIGRATE", "true").lower() == "true":
        applied = await asyncio.to_thread(db.migrate)
        if applied:
            log.info("applied migrations: %s", ", ".join(applied))
    task = asyncio.create_task(_sweeper()) if os.environ.get("BACKGROUND_JOBS", "true") == "true" else None
    yield
    if task:
        task.cancel()
    db.close_pool()


def create_app() -> FastAPI:
    s = get_settings()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    app = FastAPI(title="Meridian", lifespan=lifespan,
                  docs_url=None if s.is_production else "/api/docs", redoc_url=None,
                  openapi_url=None if s.is_production else "/api/openapi.json")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        h = resp.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=(), payment=()")
        h.setdefault("Content-Security-Policy", CSP)
        if s.cookie_secure:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resp

    @app.exception_handler(AppError)
    async def app_error(_: Request, e: AppError):
        return JSONResponse({"error": e.code, "message": e.message}, status_code=e.status_code)

    @app.exception_handler(TransitionError)
    async def transition_error(_: Request, e: TransitionError):
        return JSONResponse({"error": "invalid_transition", "message": str(e)}, status_code=409)

    for r in (public_api.router, trips.router, integrations.router, admin.router):
        app.include_router(r)
    static_dir = site.ROOT / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(site.router)   # last: owns the catch-all /{page}
    return app


app = create_app()
