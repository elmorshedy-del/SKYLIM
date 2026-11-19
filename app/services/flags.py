"""Owner switches stored in the database, so they change without a deploy."""
from __future__ import annotations

import psycopg

INSTANT_BOOKING = "instant_booking"


def enabled(conn: psycopg.Connection, key: str, default: bool = False) -> bool:
    row = conn.execute("SELECT enabled FROM flags WHERE key = %s", (key,)).fetchone()
    return default if row is None else bool(row["enabled"])


def set_flag(conn: psycopg.Connection, key: str, value: bool) -> None:
    conn.execute("""INSERT INTO flags (key, enabled, updated_at) VALUES (%s, %s, now())
                    ON CONFLICT (key) DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = now()""",
                 (key, value))
