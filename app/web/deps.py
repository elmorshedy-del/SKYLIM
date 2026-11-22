"""Shared request dependencies: clock, client IP, rate limits, admin auth, templates."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

import data
from marketing.brand import wordmark
from ..config import LOCAL_TZ, RECOMMENDED_GATES, get_settings
from ..domain.status import LABELS, Status
from ..security import ADMIN_COOKIE, MOCK_COOKIE, read_admin_session, read_mock_session

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
TEMPLATES.env.globals.update(brand=data.BRAND, brand_wordmark=Markup(wordmark()), driver=data.DRIVER,
                             vehicle_info=data.VEHICLE, policy=data.POLICY, recommended_gates=RECOMMENDED_GATES,
                             status_labels={s.value: l for s, l in LABELS.items()})
TEMPLATES.env.filters["money"] = lambda c: "—" if c is None else f"${c / 100:,.2f}"
TEMPLATES.env.filters["et"] = lambda d, fmt="%a %b %-d · %-I:%M %p": d.astimezone(LOCAL_TZ).strftime(fmt) if d else "—"


def clock() -> datetime:
    """Injected everywhere 'now' matters, so tests can freeze time."""
    return datetime.now(timezone.utc)


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Sliding-window limiter per (bucket, client). In-process: fine for one
    instance; move to Redis or the database before scaling horizontally."""

    def __init__(self):
        self._hits: dict[tuple[str, str], deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, bucket: str, key: str, limit: int, window_s: int = 60) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[(bucket, key)]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def rate_limit(bucket: str, per_minute: int):
    def dep(request: Request) -> None:
        if not limiter.check(bucket, client_ip(request), per_minute):
            raise HTTPException(status_code=429, detail="Too many requests — please wait a minute.")
    return Depends(dep)


def same_origin(request: Request) -> bool:
    """CSRF defence for cookie-authenticated POSTs (on top of SameSite=Strict)."""
    expected = urlparse(get_settings().public_base_url).netloc
    for header in ("origin", "referer"):
        v = request.headers.get(header)
        if v:
            return urlparse(v).netloc == expected
    return False


def is_admin(request: Request) -> bool:
    return read_admin_session(request.cookies.get(ADMIN_COOKIE))


def can_mock(request: Request) -> bool:
    return bool(data.TEST_TRIP.get("enabled")) and read_mock_session(request.cookies.get(MOCK_COOKIE))


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    if request.method not in ("GET", "HEAD") and not same_origin(request):
        raise HTTPException(status_code=403, detail="Cross-site request refused.")


def status_label(status: str) -> str:
    return LABELS[Status(status)]
