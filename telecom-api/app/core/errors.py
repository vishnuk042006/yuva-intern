"""Centralised error handling. Every error leaves the API in the same JSON shape:

{"error": {"code": "...", "message": "...", "request_id": "...", "details": [...]}}

Unhandled exceptions are logged with a stack trace but the client only ever sees a
generic message, so no raw server error / internals leak out.
"""
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class AppError(Exception):
    status_code = 400
    code = "bad_request"
    default_message = "Bad request"

    def __init__(self, message: str | None = None, *, details: Any = None, headers: dict | None = None):
        self.message = message or self.default_message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code, code, default_message = 400, "bad_request", "Bad request"


class UnauthorizedError(AppError):
    status_code, code, default_message = 401, "unauthorized", "Not authenticated"

    def __init__(self, message: str | None = None, **kw):
        kw.setdefault("headers", {"WWW-Authenticate": "Bearer"})
        super().__init__(message, **kw)


class ForbiddenError(AppError):
    status_code, code, default_message = 403, "forbidden", "You do not have permission to do this"


class NotFoundError(AppError):
    status_code, code = 404, "not_found"

    def __init__(self, entity: str = "Resource", **kw):
        super().__init__(f"{entity} not found", **kw)


class ConflictError(AppError):
    status_code, code, default_message = 409, "conflict", "Conflict with current state"


class RateLimitError(AppError):
    status_code, code, default_message = 429, "rate_limited", "Too many requests"


def error_body(code: str, message: str, request_id: str | None = None, details: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id, "details": details}}


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, _rid(request), exc.details),
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, str(exc.detail), _rid(request)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(p) for p in e.get("loc", ()) if p != "body"),
                "message": e.get("msg", "Invalid value"),
            }
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_body("validation_error", "Request validation failed", _rid(request), details),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning("integrity error: %s", exc.orig)
        return JSONResponse(
            status_code=409,
            content=error_body("conflict", "Request conflicts with existing data", _rid(request)),
        )

    @app.exception_handler(OperationalError)
    async def db_unavailable_handler(request: Request, exc: OperationalError):
        logger.error("database unavailable: %s", exc)
        return JSONResponse(
            status_code=503,
            content=error_body("service_unavailable", "Service temporarily unavailable", _rid(request)),
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_error_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("database error")
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "An internal error occurred", _rid(request)),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("unhandled exception")
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "An internal error occurred", _rid(request)),
        )
