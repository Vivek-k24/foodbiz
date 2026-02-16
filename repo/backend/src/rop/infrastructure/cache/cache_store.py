from __future__ import annotations

from rop.application.ports.cache import CacheStore
from rop.infrastructure.cache.redis_client import get_redis_client


class RedisCacheStore(CacheStore):
    def __init__(self, timeout_seconds: float = 1.0) -> None:
        self._timeout_seconds = timeout_seconds

    def get(self, key: str) -> str | None:
        value = get_redis_client(timeout_seconds=self._timeout_seconds).get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        get_redis_client(timeout_seconds=self._timeout_seconds).set(
            name=key,
            value=value,
            ex=ttl_seconds,
        )
