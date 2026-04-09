from __future__ import annotations

import json
import threading


def test_websocket_receives_order_created_event(client) -> None:
    session_response = client.post(
        "/v1/sessions",
        json={
            "restaurant_id": "rst_001",
            "location_id": "loc_002",
            "channel": "pickup",
            "source_type": "business_website",
        },
    )
    session_id = session_response.json()["id"]

    with client.websocket_connect("/ws?restaurant_id=rst_001&role=KITCHEN") as websocket:
        message_holder: dict[str, str] = {}
        error_holder: dict[str, Exception] = {}

        def _receive_message() -> None:
            try:
                message_holder["text"] = websocket.receive_text()
            except Exception as exc:  # pragma: no cover - assertion below covers failures
                error_holder["error"] = exc

        receiver = threading.Thread(target=_receive_message, daemon=True)
        receiver.start()

        response = client.post(
            "/v1/orders",
            json={
                "restaurant_id": "rst_001",
                "session_id": session_id,
                "lines": [{"menu_item_id": "itm_001", "quantity": 1}],
            },
        )
        assert response.status_code == 201

        receiver.join(timeout=2.0)
        assert not receiver.is_alive(), "timed out waiting for websocket event"
        assert "error" not in error_holder

        payload = json.loads(message_holder["text"])
        assert payload["event_type"] == "order.created"
        assert payload["restaurant_id"] == "rst_001"
