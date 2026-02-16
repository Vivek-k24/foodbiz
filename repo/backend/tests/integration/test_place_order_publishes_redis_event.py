from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app
from rop.infrastructure.cache.redis_client import get_redis_client


def _wait_for_message(pubsub, timeout_seconds: float = 2.0) -> str | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.2)
        if message and message.get("type") == "message":
            payload = message.get("data")
            if isinstance(payload, bytes):
                return payload.decode("utf-8")
            return str(payload)
        time.sleep(0.05)
    return None


def test_place_order_persists_and_publishes_event() -> None:
    redis_client = get_redis_client()
    pubsub = redis_client.pubsub()
    pubsub.subscribe("events:rst_001")
    pubsub.get_message(timeout=0.5)

    client = TestClient(app)
    place_order_response = client.post(
        "/v1/restaurants/rst_001/tables/tbl_001/orders",
        json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
    )
    assert place_order_response.status_code == 201
    payload = place_order_response.json()
    order_id = payload["orderId"]
    assert payload["tableId"] == "tbl_001"

    stored_order_response = client.get(f"/v1/orders/{order_id}")
    assert stored_order_response.status_code == 200
    assert stored_order_response.json()["orderId"] == order_id

    message = _wait_for_message(pubsub, timeout_seconds=2.0)
    assert message is not None

    event = json.loads(message)
    assert event["event_type"] == "order.placed"
    assert event["restaurant_id"] == "rst_001"
    assert event["payload"]["orderId"] == order_id
    assert event["payload"]["tableId"] == "tbl_001"
    assert _wait_for_message(pubsub, timeout_seconds=0.4) is None
