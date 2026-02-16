from __future__ import annotations

import logging
import time

from fastapi import FastAPI
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from rop.api.middleware.request_id import RequestIDMiddleware
from rop.api.routes.health import router as health_router
from rop.api.routes.menu import router as menu_router
from rop.api.routes.metrics import router as metrics_router
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


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="ROP Backend", version="0.1.0")
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(menu_router)

    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)

    configure_otel(app)
    return app


app = create_app()
