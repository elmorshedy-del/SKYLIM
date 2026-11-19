"""Domain errors. Services raise these; the web layer maps them to HTTP status codes."""
from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Invalid(AppError):
    status_code = 422
    code = "invalid"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class Unavailable(AppError):
    """A feature is switched off (payments not live, tracking disabled…)."""
    status_code = 503
    code = "unavailable"
