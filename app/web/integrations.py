"""Inbound machine endpoints: Stripe webhooks and location reports."""
from __future__ import annotations

import hmac
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from ..config import get_settings
from ..db import tx
from ..domain.tracking import BadReport, parse_report, parse_traccar_forward
from ..errors import Forbidden, Unavailable
from ..services import payments, tracking
from .deps import clock, rate_limit

log = logging.getLogger("meridian.integrations")
router = APIRouter(tags=["integrations"])


@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request, now: datetime = Depends(clock)):
    raw = await request.body()
    outcome = payments.handle_event(raw, request.headers.get("stripe-signature"), now=now)
    log.info("stripe webhook: %s", outcome)
    return {"received": True, "outcome": outcome}


@router.api_route("/api/tracking/osmand", methods=["GET", "POST"], dependencies=[rate_limit("tracking", 240)])
async def osmand(request: Request, now: datetime = Depends(clock)):
    """Traccar Client (phone). Always answers 200 for a well-formed report so the
    app does not queue and replay points we deliberately discard."""
    if not get_settings().tracking_enabled:
        raise Unavailable("Tracking is switched off.")
    form = dict(request.query_params)
    body = None
    ctype = request.headers.get("content-type", "")
    if "json" in ctype:
        try:
            body = json.loads(await request.body() or b"{}")
        except json.JSONDecodeError:
            return PlainTextResponse("bad json", status_code=400)
    elif "form" in ctype:
        form.update({k: v for k, v in (await request.form()).items() if isinstance(v, str)})
    try:
        fix = parse_report(form, body, now)
    except BadReport as e:
        return PlainTextResponse(str(e), status_code=400)
    with tx() as conn:
        outcome = tracking.ingest(conn, fix, now)
    if outcome == "unknown_device":
        return PlainTextResponse("unknown device", status_code=403)
    return PlainTextResponse("ok")


@router.post("/api/tracking/traccar", dependencies=[rate_limit("tracking", 240)])
async def traccar_forward(request: Request, now: datetime = Depends(clock)):
    """Positions forwarded by a Traccar server for an in-car tracker.
    Configure in traccar.xml:  forward.enable=true, forward.type=json,
    forward.url=https://<domain>/api/tracking/traccar, and
    forward.header=Authorization: Bearer <TRACCAR_FORWARD_TOKEN>."""
    s = get_settings()
    if not s.tracking_enabled:
        raise Unavailable("Tracking is switched off.")
    expected = f"Bearer {s.traccar_forward_token}"
    if not s.traccar_forward_token or not hmac.compare_digest(request.headers.get("authorization", ""), expected):
        raise Forbidden("Bad forwarding token.")
    try:
        fix = parse_traccar_forward(json.loads(await request.body() or b"{}"), now)
    except (BadReport, json.JSONDecodeError) as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    with tx() as conn:
        return {"ok": True, "outcome": tracking.ingest(conn, fix, now)}
