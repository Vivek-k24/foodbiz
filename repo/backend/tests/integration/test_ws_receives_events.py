from __future__ import annotations

import json
import queue
import sys
import threading
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app


def test_websocket_receives_order_transition_events() -> None:
    table_id = f"tbl_ws_{uuid4().hex[:8]}"
    events: "queue.Queue[str]" = queue.Queue()
    errors: "queue.Queue[Exception]" = queue.Queue()

    with TestClient(app) as client:
        with client.websocket_connect("/ws?restaurant_id=rst_001&role=KITCHEN") as websocket:

            def _reader() -> None:
                try:
                    for _ in range(5):
                        events.put(websocket.receive_text())
                except Exception as exc:
                    errors.put(exc)

            reader = threading.Thread(target=_reader, daemon=True)
            reader.start()

            open_response = client.post(f"/v1/restaurants/rst_001/tables/{table_id}/open")
            assert open_response.status_code == 200

            place_response = client.post(
                f"/v1/restaurants/rst_001/tables/{table_id}/orders",
                json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
            )
            assert place_response.status_code == 201
            order_id = place_response.json()["orderId"]

            accept_response = client.post(f"/v1/orders/{order_id}/accept")
            assert accept_response.status_code == 200

            ready_response = client.post(f"/v1/orders/{order_id}/ready")
            assert ready_response.status_code == 200

            close_response = client.post(f"/v1/restaurants/rst_001/tables/{table_id}/close")
            assert close_response.status_code == 200

            reader.join(timeout=2.0)
            assert not reader.is_alive(), "timed out waiting for websocket events"
            assert errors.empty(), "unexpected websocket read error"

    raw_messages = [events.get_nowait() for _ in range(5)]
    event_types = [json.loads(message)["event_type"] for message in raw_messages]
    assert event_types == [
        "table.opened",
        "order.placed",
        "order.accepted",
        "order.ready",
        "table.closed",
    ]
