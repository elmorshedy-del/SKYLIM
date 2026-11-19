"""Booking lifecycle. Every status change in the system goes through `assert_transition`."""
from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    REQUESTED = "requested"              # rider asked; owner has not decided
    PAYMENT_PENDING = "payment_pending"  # owner approved; slot held while rider pays
    CONFIRMED = "confirmed"              # payment verified by Stripe webhook
    EN_ROUTE = "en_route"
    ARRIVED = "arrived"
    IN_VEHICLE = "in_vehicle"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DECLINED = "declined"                # owner could not take it
    EXPIRED = "expired"                  # hold lapsed without payment

    def __str__(self) -> str:  # so f-strings and SQL params get the plain value
        return self.value


ACTIVE_TRIP = frozenset({Status.EN_ROUTE, Status.ARRIVED, Status.IN_VEHICLE})
TERMINAL = frozenset({Status.COMPLETED, Status.CANCELLED, Status.DECLINED, Status.EXPIRED})
HOLDS_CALENDAR = frozenset({Status.PAYMENT_PENDING, Status.CONFIRMED}) | ACTIVE_TRIP

_ALLOWED: dict[Status, frozenset[Status]] = {
    Status.REQUESTED: frozenset({Status.PAYMENT_PENDING, Status.DECLINED, Status.CANCELLED}),
    Status.PAYMENT_PENDING: frozenset({Status.CONFIRMED, Status.EXPIRED, Status.CANCELLED}),
    Status.CONFIRMED: frozenset({Status.EN_ROUTE, Status.CANCELLED}),
    Status.EN_ROUTE: frozenset({Status.ARRIVED, Status.CONFIRMED, Status.CANCELLED}),  # confirmed = undo a mis-tap
    Status.ARRIVED: frozenset({Status.IN_VEHICLE, Status.CANCELLED}),                 # cancelled covers a no-show
    Status.IN_VEHICLE: frozenset({Status.COMPLETED}),
}

# Buttons the owner sees on a trip in each status, in order.
OPERATIONAL_NEXT = {
    Status.CONFIRMED: Status.EN_ROUTE,
    Status.EN_ROUTE: Status.ARRIVED,
    Status.ARRIVED: Status.IN_VEHICLE,
    Status.IN_VEHICLE: Status.COMPLETED,
}

LABELS = {
    Status.REQUESTED: "Request received",
    Status.PAYMENT_PENDING: "Approved — awaiting payment",
    Status.CONFIRMED: "Confirmed",
    Status.EN_ROUTE: "Chauffeur on the way",
    Status.ARRIVED: "Chauffeur has arrived",
    Status.IN_VEHICLE: "On your journey",
    Status.COMPLETED: "Completed",
    Status.CANCELLED: "Cancelled",
    Status.DECLINED: "Not available",
    Status.EXPIRED: "Hold expired",
}


class TransitionError(Exception):
    pass


def can_transition(current: Status | str, target: Status | str) -> bool:
    return Status(target) in _ALLOWED.get(Status(current), frozenset())


def assert_transition(current: Status | str, target: Status | str) -> None:
    if not can_transition(current, target):
        raise TransitionError(f"Cannot move a booking from {current} to {target}.")
