from __future__ import annotations

import os
from functools import lru_cache

import redis


def _redis_url() -> str:
    url = os.getenv("REDIS_URL")
    if not url:
        raise RuntimeError("REDIS_URL is not set")
    return url


@lru_cache(maxsize=8)
def _build_client(redis_url: str, timeout_seconds: float) -> redis.Redis:
    return redis.Redis.from_url(
        redis_url,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
    )


def get_redis_client(timeout_seconds: float = 1.0) -> redis.Redis:
    return _build_client(_redis_url(), timeout_seconds)


def ping_redis(timeout_seconds: float = 1.0) -> bool:
    try:
        return bool(get_redis_client(timeout_seconds).ping())
    except Exception:
        return False
