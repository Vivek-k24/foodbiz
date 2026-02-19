from __future__ import annotations

from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from rop.api.middleware.request_id import get_request_id
from rop.application.use_cases.accept_order import (
    InvalidOrderTransitionError as AcceptInvalidOrderTransitionError,
)
from rop.application.use_cases.accept_order import OrderConflictError as AcceptOrderConflictError
from rop.application.use_cases.accept_order import OrderNotFoundError as AcceptOrderNotFoundError
from rop.application.use_cases.close_table import TableCloseBlockedError, TableNotOpenForCloseError
from rop.application.use_cases.get_menu import MenuNotFoundError as GetMenuNotFoundError
from rop.application.use_cases.get_order import OrderNotFoundError as GetOrderNotFoundError
from rop.application.use_cases.kitchen_queue import (
    InvalidKitchenQueueCursorError,
    InvalidKitchenQueueStatusError,
)
from rop.application.use_cases.mark_order_ready import (
    InvalidOrderTransitionError as ReadyInvalidOrderTransitionError,
)
from rop.application.use_cases.mark_order_ready import (
    OrderConflictError as ReadyOrderConflictError,
)
from rop.application.use_cases.mark_order_ready import OrderNotFoundError as ReadyOrderNotFoundError
from rop.application.use_cases.open_table import TableNotFoundError as GetTableNotFoundError
from rop.application.use_cases.place_order import (
    IdempotencyReplayMismatchError,
    MenuItemUnavailableError,
    TableNotOpenError,
)
from rop.application.use_cases.place_order import (
    MenuNotFoundError as PlaceOrderMenuNotFoundError,
)
from rop.application.use_cases.place_order import (
    TableNotFoundError as PlaceOrderTableNotFoundError,
)
from rop.application.use_cases.table_orders import (
    InvalidTableOrdersCursorError,
    InvalidTableOrdersStatusError,
)


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
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "requestId": get_request_id(),
        },
    )


def _exception_handler(status_code: int, code: str):
    async def handler(_: Request, exc: Exception) -> JSONResponse:
        details = getattr(exc, "details", None)
        return _error_response(
            status_code=status_code,
            code=code,
            message=str(exc),
            details=details if isinstance(details, dict) else None,
        )

    return handler


async def _http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    message = str(http_exc.detail) if http_exc.detail else "request failed"
    code = "HTTP_ERROR"
    if http_exc.status_code == 404:
        code = "NOT_FOUND"
    elif http_exc.status_code == 400:
        code = "BAD_REQUEST"
    elif http_exc.status_code == 409:
        code = "CONFLICT"
    return _error_response(
        status_code=http_exc.status_code,
        code=code,
        message=message,
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
    mappings: list[tuple[type[Exception], int, str]] = [
        (GetMenuNotFoundError, 404, "MENU_NOT_FOUND"),
        (PlaceOrderMenuNotFoundError, 404, "MENU_NOT_FOUND"),
        (GetOrderNotFoundError, 404, "ORDER_NOT_FOUND"),
        (AcceptOrderNotFoundError, 404, "ORDER_NOT_FOUND"),
        (ReadyOrderNotFoundError, 404, "ORDER_NOT_FOUND"),
        (GetTableNotFoundError, 404, "TABLE_NOT_FOUND"),
        (PlaceOrderTableNotFoundError, 404, "TABLE_NOT_FOUND"),
        (TableNotOpenError, 409, "TABLE_NOT_OPEN"),
        (TableNotOpenForCloseError, 409, "TABLE_NOT_OPEN"),
        (TableCloseBlockedError, 409, "TABLE_CLOSE_BLOCKED"),
        (MenuItemUnavailableError, 400, "MENU_ITEM_UNAVAILABLE"),
        (
            IdempotencyReplayMismatchError,
            409,
            "IDEMPOTENCY_KEY_REPLAY_DIFFERENT_PAYLOAD",
        ),
        (
            AcceptInvalidOrderTransitionError,
            409,
            "INVALID_ORDER_TRANSITION",
        ),
        (
            ReadyInvalidOrderTransitionError,
            409,
            "INVALID_ORDER_TRANSITION",
        ),
        (AcceptOrderConflictError, 409, "CONFLICT"),
        (ReadyOrderConflictError, 409, "CONFLICT"),
        (InvalidKitchenQueueStatusError, 400, "INVALID_KITCHEN_QUEUE_STATUS"),
        (InvalidKitchenQueueCursorError, 400, "INVALID_KITCHEN_QUEUE_CURSOR"),
        (InvalidTableOrdersStatusError, 400, "INVALID_TABLE_ORDERS_STATUS"),
        (InvalidTableOrdersCursorError, 400, "INVALID_TABLE_ORDERS_CURSOR"),
    ]

    for exc_cls, status_code, code in mappings:
        app.add_exception_handler(exc_cls, _exception_handler(status_code, code))

    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
