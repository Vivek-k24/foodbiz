from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from redis import asyncio as redis_asyncio

logger = logging.getLogger(__name__)


def _decode_value(value: bytes | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


async def start_redis_fanout(app_state: Any) -> None:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("redis_fanout_not_started", extra={"reason": "REDIS_URL missing"})
        return

    backoff_seconds = 1.0
    while True:
        client: redis_asyncio.Redis | None = None
        pubsub: redis_asyncio.client.PubSub | None = None
        try:
            client = redis_asyncio.from_url(redis_url)
            pubsub = client.pubsub()
            await pubsub.psubscribe("events:*")
            logger.info("redis_fanout_subscribed", extra={"pattern": "events:*"})
            backoff_seconds = 1.0

            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    await asyncio.sleep(0.05)
                    continue

                channel = _decode_value(message.get("channel"))
                payload = _decode_value(message.get("data"))
                if not channel or not payload:
                    continue

                _, _, restaurant_id = channel.partition(":")
                if not restaurant_id:
                    logger.warning("redis_fanout_invalid_channel", extra={"channel": channel})
                    continue

                await app_state.ws_manager.broadcast(
                    restaurant_id=restaurant_id,
                    message_json_str=payload,
                )
        except asyncio.CancelledError:
            logger.info("redis_fanout_cancelled")
            raise
        except Exception:
            logger.exception(
                "redis_fanout_error",
                extra={"backoff_seconds": backoff_seconds},
            )
            await asyncio.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 5.0)
        finally:
            if pubsub is not None:
                pubsub_aclose = getattr(pubsub, "aclose", None)
                if callable(pubsub_aclose):
                    await pubsub_aclose()
                else:
                    await pubsub.close()
            if client is not None:
                client_aclose = getattr(client, "aclose", None)
                if callable(client_aclose):
                    await client_aclose()
                else:
                    await client.close()
