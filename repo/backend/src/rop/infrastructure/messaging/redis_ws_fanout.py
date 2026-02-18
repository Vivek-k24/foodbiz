from __future__ import annotations

from rop.infrastructure.messaging.redis_event_listener import start_redis_fanout


async def start_redis_ws_fanout(app_state) -> None:
    await start_redis_fanout(app_state)
