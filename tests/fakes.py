"""Test doubles for external providers."""
from __future__ import annotations


class FakeGateway:
    """Records Checkout sessions and refunds instead of calling Stripe."""

    def __init__(self):
        self.sessions: list[dict] = []
        self.refunds: list[tuple] = []

    def create_checkout(self, params, idempotency_key):
        sid = f"cs_test_{len(self.sessions) + 1}"
        self.sessions.append({"id": sid, "params": params, "key": idempotency_key})
        return {"id": sid, "url": f"https://checkout.stripe.test/{sid}", "livemode": False}

    def refund(self, payment_intent_id, amount_cents, idempotency_key):
        self.refunds.append((payment_intent_id, amount_cents, idempotency_key))
        return {"id": "re_1", "status": "succeeded"}
