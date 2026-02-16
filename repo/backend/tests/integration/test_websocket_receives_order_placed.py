from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app


def test_websocket_receives_order_placed_event() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws?restaurant_id=rst_001&role=KITCHEN") as websocket:
            message_holder: dict[str, str] = {}
            error_holder: dict[str, Exception] = {}

            def _receive_message() -> None:
                try:
                    message_holder["text"] = websocket.receive_text()
                except Exception as exc:
                    error_holder["error"] = exc

            receiver = threading.Thread(target=_receive_message, daemon=True)
            receiver.start()

            response = client.post(
                "/v1/restaurants/rst_001/tables/tbl_001/orders",
                json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
            )
            assert response.status_code == 201

            receiver.join(timeout=2.0)
            assert not receiver.is_alive(), "timed out waiting for websocket event"
            assert "error" not in error_holder

            payload = json.loads(message_holder["text"])
            assert payload["event_type"] == "order.placed"
            assert payload["restaurant_id"] == "rst_001"
