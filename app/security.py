"""Opaque customer tokens, admin password hashing and the signed admin session.

Usage (one-off, on your own machine):
    python -m app.security hash-password      # prints ADMIN_PASSWORD_HASH
    python -m app.security new-secret         # prints a SECRET_KEY / TRACKER_DEVICE_ID
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sys
import time

from .config import get_settings

ADMIN_COOKIE = "mr_admin"
MOCK_COOKIE = "mr_mock"
ADMIN_SESSION_SECONDS = 12 * 3600


# ------------------------------------------------------------------ tokens
def new_token() -> str:
    """256-bit URL-safe random token. Only its hash is ever stored."""
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def trip_token(booking_id) -> str:
    """The rider's private trip-link token, derived (not stored) so later emails
    can include the same link. Only token_hash(trip_token(id)) is persisted.
    Rotating SECRET_KEY invalidates every outstanding trip link."""
    key = get_settings().secret_key.encode()
    mac = hmac.new(key, b"trip:" + str(booking_id).encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")


def hash_device_id(device_id: str) -> str:
    return hashlib.sha256(("device:" + device_id).encode("utf-8")).hexdigest()


def booking_ref() -> str:
    """Human-friendly reference, e.g. CL-7KQ2X9 (no 0/O/1/I to avoid misreading). Printed on the
    client's card statement, so it must stay within Stripe's descriptor rules (letters, digits, hyphen)."""
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "CL-" + "".join(secrets.choice(alphabet) for _ in range(6))


# --------------------------------------------------------------- passwords
def hash_password(password: str, *, n: int = 2**15, r: int = 8, p: int = 1) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=64 * 1024 * 1024, dklen=32)
    return "scrypt$%d$%d$%d$%s$%s" % (n, r, p, base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, dk_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), n=int(n), r=int(r),
                            p=int(p), maxmem=64 * 1024 * 1024, dklen=32)
        return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except Exception:
        return False


# ----------------------------------------------------------- admin session
def _sign(payload: bytes) -> str:
    key = get_settings().secret_key.encode()
    return base64.urlsafe_b64encode(hmac.new(key, payload, hashlib.sha256).digest()).decode().rstrip("=")


def _make_session(scope: bytes = b"") -> str:
    body = base64.urlsafe_b64encode(json.dumps(
        {"exp": int(time.time()) + ADMIN_SESSION_SECONDS, "n": secrets.token_hex(8)}
    ).encode()).decode().rstrip("=")
    return body + "." + _sign(scope + body.encode())


def _read_session(cookie: str | None, scope: bytes = b"") -> bool:
    if not cookie or "." not in cookie or not get_settings().secret_key:
        return False
    body, sig = cookie.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(scope + body.encode())):
        return False
    try:
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except Exception:
        return False
    return int(data.get("exp", 0)) > time.time()


def make_admin_session() -> str:
    return _make_session()


def read_admin_session(cookie: str | None) -> bool:
    return _read_session(cookie)


def make_mock_session() -> str:
    """Separate, API-scoped capability; it can never authorize admin routes."""
    return _make_session(b"mock:")


def read_mock_session(cookie: str | None) -> bool:
    return _read_session(cookie, b"mock:")


if __name__ == "__main__":  # pragma: no cover - operator utility
    import getpass

    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "hash-password":
        pw = getpass.getpass("Admin password (16+ characters): ")
        if len(pw) < 16:
            sys.exit("Use at least 16 characters.")
        if pw != getpass.getpass("Repeat: "):
            sys.exit("Passwords did not match.")
        print(hash_password(pw))
    elif cmd == "new-secret":
        print(secrets.token_urlsafe(48))
    else:
        sys.exit(__doc__)
