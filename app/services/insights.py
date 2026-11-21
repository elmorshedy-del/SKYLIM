"""First-party funnel analytics from our own tables — no third-party tags needed.

quotes (every price shown) -> bookings (reservations/requests) -> payments (paid)
-> completed trips, with lost demand (quotes that met a full calendar) and
channel attribution. This is the seed of the owner's own analytics platform.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import psycopg


def funnel(conn: psycopg.Connection, now: datetime, days: int = 30) -> dict:
    since = now - timedelta(days=days)
    q = conn.execute(
        """SELECT count(*) AS quotes,
                  count(*) FILTER (WHERE eligible) AS bookable,
                  count(*) FILTER (WHERE availability IN ('unavailable', 'day_full')) AS lost_full,
                  count(*) FILTER (WHERE 'authority_arranged' = ANY(decision_reasons)
                                      OR 'custom_route' = ANY(decision_reasons)) AS needs_arranging
           FROM quotes WHERE created_at >= %s
             AND COALESCE(attribution->>'source', '') <> 'test_trip'""", (since,)).fetchone()
    b = conn.execute(
        """SELECT count(*) AS reservations,
                  count(*) FILTER (WHERE instant) AS instant,
                  count(*) FILTER (WHERE status IN ('confirmed','en_route','arrived','in_vehicle','completed')) AS paid,
                  count(*) FILTER (WHERE status = 'completed') AS completed,
                  count(*) FILTER (WHERE status IN ('cancelled','declined','expired')) AS lost_after_request
           FROM bookings WHERE created_at >= %s AND NOT is_test""", (since,)).fetchone()
    rev = conn.execute(
        """SELECT COALESCE(sum(p.amount_cents - p.refunded_cents), 0) AS cents
           FROM payments p JOIN bookings b ON b.id = p.booking_id WHERE p.paid_at >= %s AND NOT b.is_test""",
        (since,)).fetchone()
    sources = conn.execute(
        """SELECT COALESCE(attribution->>'utm_source', source, 'direct') AS channel,
                  count(*) AS reservations,
                  count(*) FILTER (WHERE status IN ('confirmed','en_route','arrived','in_vehicle','completed')) AS paid
           FROM bookings WHERE created_at >= %s AND NOT is_test GROUP BY 1 ORDER BY 2 DESC LIMIT 6""",
        (since,)).fetchall()

    def rate(a, b_):
        return round(100 * a / b_) if b_ else None

    return {
        "days": days, **q, **b, "revenue_cents": rev["cents"], "sources": sources,
        "quote_to_reservation": rate(b["reservations"], q["bookable"]),
        "reservation_to_paid": rate(b["paid"], b["reservations"]),
    }
