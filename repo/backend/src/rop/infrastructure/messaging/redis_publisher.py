from __future__ import annotations

import json
import logging
from typing import Any

from rop.infrastructure.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class RedisEventPublisher:
    def __init__(self, timeout_seconds: float = 1.0) -> None:
        self._timeout_seconds = timeout_seconds

    def publish(self, channel: str, message: str) -> None:
        try:
            get_redis_client(timeout_seconds=self._timeout_seconds).publish(channel, message)
        except Exception:
            logger.exception("redis_publish_failed", extra={"channel": channel})

    def publish_json(self, restaurant_id: str, payload: dict[str, Any]) -> None:
        self.publish(f"events:{restaurant_id}", json.dumps(payload))
