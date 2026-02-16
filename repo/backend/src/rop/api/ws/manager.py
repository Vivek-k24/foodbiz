from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._socket_to_restaurant: dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocket, restaurant_id: str, role: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[restaurant_id].add(websocket)
            self._socket_to_restaurant[websocket] = restaurant_id
        logger.info(
            "ws_client_connected",
            extra={"restaurant_id": restaurant_id, "role": role},
        )

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            restaurant_id = self._socket_to_restaurant.pop(websocket, None)
            if restaurant_id is None:
                return
            sockets = self._connections.get(restaurant_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(restaurant_id, None)
        logger.info("ws_client_disconnected", extra={"restaurant_id": restaurant_id})

    async def broadcast(self, restaurant_id: str, message_json_str: str) -> None:
        async with self._lock:
            targets = list(self._connections.get(restaurant_id, set()))

        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_text(message_json_str)
            except Exception:
                stale.append(websocket)

        for websocket in stale:
            await self.unregister(websocket)
