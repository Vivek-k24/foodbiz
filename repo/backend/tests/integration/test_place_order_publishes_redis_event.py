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
        json={
            "lines": [
                {
                    "itemId": "itm_001",
                    "quantity": 1,
                    "notes": "well done",
                    "modifiers": [
                        {"code": "extra_mozzarella", "label": "Extra Mozzarella", "value": "true"},
                        {"code": "crust", "label": "Crust", "value": "thin"},
                    ],
                },
                {
                    "itemId": "itm_003",
                    "quantity": 1,
                    "modifiers": [
                        {"code": "pasta", "label": "Pasta", "value": "rigatoni"},
                        {"code": "add_guanciale", "label": "Add Guanciale", "value": "true"},
                    ],
                },
                {
                    "itemId": "drink_003",
                    "quantity": 1,
                    "modifiers": [
                        {"code": "milk", "label": "Milk", "value": "oat"},
                        {"code": "syrup", "label": "Syrup", "value": "vanilla"},
                    ],
                },
            ]
        },
    )
    assert place_order_response.status_code == 201
    payload = place_order_response.json()
    order_id = payload["orderId"]
    assert payload["tableId"] == "tbl_001"
    assert len(payload["lines"]) == 3
    margherita_line = next(line for line in payload["lines"] if line["itemId"] == "itm_001")
    assert margherita_line["modifiers"][0]["code"] == "extra_mozzarella"
    assert margherita_line["notes"] == "well done"

    stored_order_response = client.get(f"/v1/orders/{order_id}")
    assert stored_order_response.status_code == 200
    stored_payload = stored_order_response.json()
    assert stored_payload["orderId"] == order_id
    carbonara_line = next(line for line in stored_payload["lines"] if line["itemId"] == "itm_003")
    latte_line = next(line for line in stored_payload["lines"] if line["itemId"] == "drink_003")
    assert carbonara_line["modifiers"][0]["code"] == "pasta"
    assert latte_line["modifiers"][1]["value"] == "vanilla"

    queue_response = client.get("/v1/restaurants/rst_001/kitchen/orders?status=PLACED&limit=10")
    assert queue_response.status_code == 200
    queue_payload = queue_response.json()
    queue_order = next(item for item in queue_payload["orders"] if item["orderId"] == order_id)
    queue_margherita = next(line for line in queue_order["lines"] if line["itemId"] == "itm_001")
    assert queue_margherita["modifiers"][1]["value"] == "thin"

    message = _wait_for_message(pubsub, timeout_seconds=2.0)
    assert message is not None

    event = json.loads(message)
    assert event["event_type"] == "order.placed"
    assert event["restaurant_id"] == "rst_001"
    assert event["payload"]["orderId"] == order_id
    assert event["payload"]["tableId"] == "tbl_001"
    assert event["payload"]["lines"][0]["notes"] == "well done"
    assert event["payload"]["lines"][0]["modifiers"][0]["code"] == "extra_mozzarella"
    assert event["payload"]["lines"][2]["modifiers"][0]["value"] == "oat"
    assert _wait_for_message(pubsub, timeout_seconds=0.4) is None
