"""Domain errors raised by services and mapped to HTTP / bot replies by the routers.

Codes follow the SCRUM-116 error shape ``{"error": {"code": ..., "message": ...}}``.
"""

from __future__ import annotations


class ServiceError(Exception):
    code = "SERVICE_ERROR"
    http_status = 400

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class NotFoundError(ServiceError):
    code = "NOT_FOUND"
    http_status = 404


class PermissionDeniedError(ServiceError):
    code = "FORBIDDEN"
    http_status = 403


class ConflictError(ServiceError):
    """State or version conflict, e.g. a stale ``Expense.version`` (409)."""

    code = "CONFLICT"
    http_status = 409


class ValidationError(ServiceError):
    code = "INVALID_INPUT"
    http_status = 422
