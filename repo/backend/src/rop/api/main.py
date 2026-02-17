from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from rop.api.middleware.request_id import RequestIDMiddleware
from rop.api.routes.health import router as health_router
from rop.api.routes.menu import router as menu_router
from rop.api.routes.metrics import router as metrics_router
from rop.api.routes.orders import router as orders_router
from rop.api.routes.tables import router as tables_router
from rop.api.ws.manager import ConnectionManager
from rop.api.ws.routes import router as ws_router
from rop.infrastructure.messaging.redis_event_listener import start_redis_fanout
from rop.infrastructure.observability.logging_config import configure_logging
from rop.infrastructure.observability.otel import configure_otel

logger = logging.getLogger("rop.api.access")

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        path = request.url.path
        method = request.method
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            REQUEST_COUNT.labels(method=method, path=path, status_code="500").inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration_ms / 1000)
            logger.exception(
                "request_error",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise

        duration_ms = (time.perf_counter() - started) * 1000
        REQUEST_COUNT.labels(method=method, path=path, status_code=str(response.status_code)).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(duration_ms / 1000)
        logger.info(
            "request_complete",
            extra={
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ws_manager = ConnectionManager()
    fanout_task = asyncio.create_task(start_redis_fanout(app.state))
    app.state.redis_fanout_task = fanout_task
    try:
        yield
    finally:
        fanout_task.cancel()
        with suppress(asyncio.CancelledError):
            await fanout_task


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="ROP Backend", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(menu_router)
    app.include_router(tables_router)
    app.include_router(orders_router)
    app.include_router(ws_router)

    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    configure_otel(app)
    return app


app = create_app()
