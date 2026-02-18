from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app
from rop.infrastructure.cache.redis_client import get_redis_client


def _pull_event_types(pubsub, count: int, timeout_seconds: float = 2.0) -> list[str]:
    deadline = time.time() + timeout_seconds
    event_types: list[str] = []
    while time.time() < deadline and len(event_types) < count:
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.2)
        if not message or message.get("type") != "message":
            time.sleep(0.05)
            continue
        payload = message.get("data")
        raw = payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)
        event_types.append(json.loads(raw)["event_type"])
    return event_types


def test_redis_pubsub_emits_events_for_order_transitions() -> None:
    redis_client = get_redis_client()
    pubsub = redis_client.pubsub()
    pubsub.subscribe("events:rst_001")
    pubsub.get_message(timeout=0.5)

    with TestClient(app) as client:
        place_response = client.post(
            "/v1/restaurants/rst_001/tables/tbl_001/orders",
            json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
        )
        assert place_response.status_code == 201
        order_id = place_response.json()["orderId"]

        accept_response = client.post(f"/v1/orders/{order_id}/accept")
        assert accept_response.status_code == 200
        ready_response = client.post(f"/v1/orders/{order_id}/ready")
        assert ready_response.status_code == 200

    event_types = _pull_event_types(pubsub, count=3, timeout_seconds=2.0)
    assert event_types == ["order.placed", "order.accepted", "order.ready"]
