from __future__ import annotations

from rop.application.ports.publisher import EventPublisher
from rop.infrastructure.cache.redis_client import get_redis_client


class RedisEventPublisher(EventPublisher):
    def __init__(self, timeout_seconds: float = 1.0) -> None:
        self._timeout_seconds = timeout_seconds

    def publish(self, channel: str, message: str) -> None:
        get_redis_client(timeout_seconds=self._timeout_seconds).publish(channel, message)
