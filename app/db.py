"""PostgreSQL access: one pool, explicit transactions, numbered migrations."""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import get_settings

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"

# Fixed identifiers for the launch fleet, so seeds are idempotent across deploys.
VEHICLE_ID = uuid.UUID("6f1c2a52-0e0b-4d61-9b1e-3c1d00000001")
DRIVER_ID = uuid.UUID("6f1c2a52-0e0b-4d61-9b1e-3c1d00000101")
# Hidden calendar for the owner's $1 test trips: inactive, so it never appears in the fleet or availability.
TEST_VEHICLE_ID = uuid.UUID("6f1c2a52-0e0b-4d61-9b1e-3c1d00000ff1")
TEST_DRIVER_ID = uuid.UUID("6f1c2a52-0e0b-4d61-9b1e-3c1d00000ff2")

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            get_settings().database_url,
            min_size=1,
            max_size=int(os.environ.get("DB_POOL_MAX", "8")),
            kwargs={"row_factory": dict_row, "autocommit": False},
            open=True,
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def tx() -> Iterator[psycopg.Connection]:
    """A single transaction: commits on success, rolls back on any exception."""
    with pool().connection() as conn:
        with conn.transaction():
            yield conn


def migrate(database_url: str | None = None) -> list[str]:
    """Apply every migrations/NNN_*.sql not yet recorded. Safe to run on each boot.

    A session-level advisory lock stops two app instances migrating at once.
    """
    url = database_url or get_settings().database_url
    applied: list[str] = []
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(727001)")
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
            for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
                if path.stem in done:
                    continue
                with conn.transaction():
                    conn.execute(path.read_text())
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
                applied.append(path.stem)
            seed(conn)
        finally:
            conn.execute("SELECT pg_advisory_unlock(727001)")
    return applied


def seed(conn: psycopg.Connection) -> None:
    """The one real vehicle and the owner-driver. Names/plates come from data.py
    and admin edits; this never overwrites a plate already entered in admin."""
    import data
    from .security import hash_device_id

    v, d = data.VEHICLE, data.DRIVER
    conn.execute(
        """INSERT INTO vehicles (id, code, display_name, color, max_passengers)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name,
               color = EXCLUDED.color, max_passengers = EXCLUDED.max_passengers""",
        (VEHICLE_ID, v["code"], v["display_name"], v.get("color"), v["max_passengers"]),
    )
    conn.execute(
        """INSERT INTO drivers (id, code, display_name) VALUES (%s, %s, %s)
           ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name""",
        (DRIVER_ID, d["code"], d["display_name"]))
    conn.execute(
        """INSERT INTO vehicles (id, code, display_name, max_passengers, active) VALUES (%s, %s, %s, %s, false)
           ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name""",
        (TEST_VEHICLE_ID, "test-trip-vehicle", v["display_name"], v["max_passengers"]))
    conn.execute(
        """INSERT INTO drivers (id, code, display_name, active) VALUES (%s, %s, %s, false)
           ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name""",
        (TEST_DRIVER_ID, "test-trip-driver", d["display_name"]))
    s = get_settings()
    for raw, kind, label in ((s.tracker_phone_id, "phone", "Chauffeur phone (Traccar Client)"),
                             (s.tracker_vehicle_id, "vehicle", "In-car tracker")):
        if raw:
            conn.execute(
                """INSERT INTO trackers (device_hash, kind, driver_id, vehicle_id, label)
                   VALUES (%s, %s, %s, %s, %s) ON CONFLICT (device_hash) DO NOTHING""",
                (hash_device_id(raw), kind, DRIVER_ID if kind == "phone" else None,
                 VEHICLE_ID if kind == "vehicle" else None, label))
