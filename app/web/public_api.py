"""Public JSON API used by the website: config, quotes, booking requests, inquiries."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

import data
from ..config import get_settings, payments_live
from ..db import tx
from ..domain.catalog import get_catalog
from ..domain.preferences import MODE_DEFAULTS, JourneyPreferences
from ..domain.pricing import QuoteInputError, TripRequest, parse_local_pickup
from ..errors import AppError, Invalid
from ..services import bookings, payments, quotes
from ..services.notifications import trip_url
from .deps import clock, rate_limit

router = APIRouter(prefix="/api", tags=["public"])

EMAIL_RE = re.compile(r"^[^\s@]{1,64}@[^\s@]{1,190}\.[A-Za-z]{2,24}$")


def _clean(v: Optional[str]) -> Optional[str]:
    """Collapse whitespace; empty becomes None."""
    if v is None:
        return None
    v = " ".join(v.split())
    return v or None


def _valid_email(v: str) -> str:
    if not EMAIL_RE.match(v):
        raise ValueError("enter a valid email address")
    return v.lower()


class Strict(BaseModel):
    """Unknown fields are rejected — a browser cannot smuggle in an amount or vehicle."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


ATTRIBUTION_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "gbraid",
                    "wbraid", "fbclid", "msclkid", "referrer", "landing_page", "ga_client_id", "first_seen"}


def _attribution(raw: Optional[dict]) -> Optional[dict]:
    """Keep only known marketing keys, as short strings. No personal data is accepted here."""
    if not raw:
        return None
    clean = {k: str(v)[:300] for k, v in raw.items() if k in ATTRIBUTION_KEYS and v not in (None, "")}
    return clean or None


class QuoteIn(Strict):
    service: Literal["transfer", "hourly"] = "transfer"
    origin: str = Field(max_length=40)
    destination: Optional[str] = Field(default=None, max_length=40)
    hours: Optional[float] = Field(default=None, ge=1, le=24)
    pickup_local: str = Field(max_length=20, description="New York wall-clock time, YYYY-MM-DDTHH:MM")
    passengers: int = Field(ge=1, le=20)
    large_bags: int = Field(ge=0, le=20)
    carry_ons: int = Field(default=0, ge=0, le=20)
    session_id: Optional[str] = Field(default=None, max_length=64)
    attribution: Optional[dict] = None


class ContactIn(Strict):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=254)
    phone: str = Field(min_length=7, max_length=25)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _valid_email(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if not 10 <= len(re.sub(r"\D", "", v)) <= 15:
            raise ValueError("enter a valid mobile number")
        return v


class TripIn(Strict):
    pickup_address: str = Field(min_length=5, max_length=300)
    dropoff_address: str = Field(min_length=3, max_length=300)
    flight_number: Optional[str] = Field(default=None, max_length=12, pattern=r"^[A-Za-z0-9 ]*$")
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("pickup_address", "dropoff_address", "flight_number", "notes")
    @classmethod
    def _tidy(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v)


class BookingIn(Strict):
    quote_id: uuid.UUID
    contact: ContactIn
    trip: TripIn
    preferences: JourneyPreferences = JourneyPreferences()
    remember_preferences: bool = False
    accept_policy_version: str = Field(max_length=40)
    source: Optional[str] = Field(default=None, max_length=120)
    attribution: Optional[dict] = None
    website: str = Field(default="", max_length=0, description="honeypot — must stay empty")


class InquiryIn(Strict):
    kind: Literal["custom_quote", "waitlist", "corporate"] = "custom_quote"
    email: str = Field(max_length=254)
    name: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=25)
    message: Optional[str] = Field(default=None, max_length=1500)
    source: Optional[str] = Field(default=None, max_length=120)
    website: str = Field(default="", max_length=0)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _valid_email(v)


# ------------------------------------------------------------------- routes
@router.get("/config")
def public_config() -> dict:
    """What the website may show. Features that are off are hidden, not faked."""
    s, cat = get_settings(), get_catalog()
    p = cat.params
    return {
        "payments_live": payments_live(s),
        "payment_methods": list(s.payment_methods_display),
        "tracking": s.tracking_enabled,
        "pricing_approved": cat.pricing_approved,
        "min_notice_hours": round(s.min_notice_minutes / 60),
        "hourly": {"cents": p["hourly_cents"], "min_hours": p["hourly_min_hours"], "max_hours": p["hourly_max_hours"]},
        "policy": {"version": cat.policy["version"], "summary": cat.policy["summary"],
                   "free_cancel_hours": cat.policy["free_cancel_hours"]},
        "vehicle": {"name": cat.vehicle["class_name"], "max_passengers": cat.vehicle["max_passengers"],
                    "luggage_capacity": cat.vehicle["luggage_capacity"], "luggage_guide": cat.vehicle["luggage_guide"]},
        "amenities": {k: v["label"] for k, v in cat.amenities.items() if v["available"]},
        "places": {k: {"name": pl.name, "short": pl.short, "group": pl.group, "airport": pl.is_airport}
                   for k, pl in cat.places.items()},
        "mode_defaults": {m.value: {k: v.value for k, v in d.items()} for m, d in MODE_DEFAULTS.items()},
    }


@router.post("/quotes", dependencies=[rate_limit("quotes", 30)])
def create_quote(body: QuoteIn, now: datetime = Depends(clock)) -> dict:
    try:
        req = TripRequest(service=body.service, origin=body.origin,
                          destination=body.destination if body.service == "transfer" else None,
                          hours=body.hours if body.service == "hourly" else None,
                          pickup_at=parse_local_pickup(body.pickup_local), passengers=body.passengers,
                          large_bags=body.large_bags, carry_ons=body.carry_ons)
        with tx() as conn:
            return quotes.create_quote(conn, req, cat=get_catalog(), settings=get_settings(), now=now,
                                       session_id=body.session_id, attribution=_attribution(body.attribution))
    except QuoteInputError as e:
        raise Invalid(str(e))


@router.post("/bookings", status_code=201, dependencies=[rate_limit("bookings", 6)])
def create_booking(body: BookingIn, now: datetime = Depends(clock)) -> dict:
    """Reserve. Clean trips with enough notice are held and sent straight to payment
    (instant); anything that needs a human look becomes a request for approval.
    The server decides which — never the browser."""
    s = get_settings()
    with tx() as conn:
        q = conn.execute("SELECT * FROM quotes WHERE id = %s", (body.quote_id,)).fetchone()
        instant = bool(q) and quotes.instant_allowed(conn, eligible=q["eligible"], needs_review=q["needs_review"],
                                                     pickup_at=q["pickup_at"], now=now, s=s)
        b, token = bookings.create(
            conn, quote_id=body.quote_id,
            contact=bookings.Contact(body.contact.name, body.contact.email, body.contact.phone),
            trip=bookings.TripDetails(body.trip.pickup_address, body.trip.dropoff_address,
                                      body.trip.flight_number, body.trip.notes),
            preferences=body.preferences, remember=body.remember_preferences,
            accepted_policy_version=body.accept_policy_version, source=body.source,
            cat=get_catalog(), now=now, attribution=_attribution(body.attribution), instant=instant, settings=s)
    checkout_url = None
    if instant:
        try:
            checkout_url = payments.start_checkout(token, now=now, s=s)
        except AppError:
            checkout_url = None          # the trip page offers "Pay securely" with the same hold
    return {"booking_id": str(b["id"]), "ref": b["ref"], "status": b["status"], "instant": instant,
            "amount_cents": b["amount_cents"], "trip_url": trip_url(b["id"]), "trip_token": token,
            "checkout_url": checkout_url}


@router.post("/inquiries", status_code=201, dependencies=[rate_limit("inquiries", 5)])
def create_inquiry(body: InquiryIn, now: datetime = Depends(clock)) -> dict:
    with tx() as conn:
        row = conn.execute(
            """INSERT INTO inquiries (kind, email, name, phone, message, source, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (body.kind, body.email, _clean(body.name), _clean(body.phone), body.message, body.source, now)
        ).fetchone()
        owner = get_settings().owner_email
        if owner:
            conn.execute(
                """INSERT INTO outbox (dedupe_key, kind, to_email, subject, body_text)
                   VALUES (%s, 'inquiry', %s, %s, %s)""",
                (f"inquiry:{row['id']}", owner, f"New {body.kind.replace('_', ' ')} from {body.email}",
                 f"From: {body.name or '—'} · {body.email} · {body.phone or '—'}\n\n{body.message or ''}\n\n"
                 f"Reply directly to the rider. — {data.BRAND['short']} website"))
    return {"ok": True}
