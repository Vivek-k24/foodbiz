from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from rop.api.ws.manager import ConnectionManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    restaurant_id = websocket.query_params.get("restaurant_id")
    role = websocket.query_params.get("role", "UNKNOWN")
    if not restaurant_id:
        await websocket.close(code=1008, reason="restaurant_id query parameter is required")
        return

    manager: ConnectionManager = websocket.app.state.ws_manager
    await manager.register(websocket=websocket, restaurant_id=restaurant_id, role=role)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.unregister(websocket)
    except Exception:
        logger.exception("ws_connection_error", extra={"restaurant_id": restaurant_id})
        await manager.unregister(websocket)
