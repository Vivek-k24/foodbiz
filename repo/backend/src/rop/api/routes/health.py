from __future__ import annotations

from fastapi import APIRouter, Response, status

from rop.infrastructure.cache.redis_client import ping_redis
from rop.infrastructure.db.session import ping_database

router = APIRouter()


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(response: Response) -> dict[str, object]:
    postgres_ready = ping_database(timeout_seconds=1.0)
    redis_ready = ping_redis(timeout_seconds=1.0)

    if postgres_ready and redis_ready:
        return {"status": "ok"}

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "unavailable",
        "checks": {"postgres": postgres_ready, "redis": redis_ready},
    }
