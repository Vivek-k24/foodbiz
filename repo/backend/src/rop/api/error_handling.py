from __future__ import annotations

from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from rop.api.middleware.request_id import get_request_id
from rop.domain.errors import ConflictError, DomainError, NotFoundError, ValidationError


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "message": message, "details": details or {}},
            "requestId": get_request_id(),
        },
    )


async def _domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    domain_exc = cast(DomainError, exc)
    status_code = 400
    if isinstance(domain_exc, NotFoundError):
        status_code = 404
    elif isinstance(domain_exc, ConflictError):
        status_code = 409
    elif isinstance(domain_exc, ValidationError):
        status_code = 400
    return _error_response(
        status_code=status_code,
        code=domain_exc.code,
        message=str(domain_exc),
        details=domain_exc.details,
    )


async def _http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    default_code = "HTTP_ERROR"
    if http_exc.status_code == 404:
        default_code = "NOT_FOUND"
    elif http_exc.status_code == 409:
        default_code = "CONFLICT"
    elif http_exc.status_code == 400:
        default_code = "BAD_REQUEST"
    return _error_response(
        status_code=http_exc.status_code,
        code=default_code,
        message=str(http_exc.detail),
    )


async def _validation_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    validation_exc = cast(RequestValidationError, exc)
    return _error_response(
        status_code=400,
        code="INVALID_REQUEST",
        message="request validation failed",
        details={"errors": validation_exc.errors()},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
