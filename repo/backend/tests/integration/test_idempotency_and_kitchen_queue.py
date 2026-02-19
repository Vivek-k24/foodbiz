from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app
from rop.infrastructure.db.models.order import OrderModel
from rop.infrastructure.db.session import get_engine


def test_place_order_idempotency_creates_single_row() -> None:
    with TestClient(app) as client:
        first = client.post(
            "/v1/restaurants/rst_001/tables/tbl_001/orders",
            headers={"Idempotency-Key": "test-key-001"},
            json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
        )
        assert first.status_code == 201

        second = client.post(
            "/v1/restaurants/rst_001/tables/tbl_001/orders",
            headers={"Idempotency-Key": "test-key-001"},
            json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
        )
        assert second.status_code == 201
        assert first.json()["orderId"] == second.json()["orderId"]

    with Session(get_engine()) as session:
        count = session.scalar(
            select(func.count())
            .select_from(OrderModel)
            .where(
                OrderModel.restaurant_id == "rst_001",
                OrderModel.table_id == "tbl_001",
                OrderModel.idempotency_key == "test-key-001",
            )
        )
        assert count == 1


def test_place_order_idempotency_mismatch_returns_409() -> None:
    with TestClient(app) as client:
        first = client.post(
            "/v1/restaurants/rst_001/tables/tbl_001/orders",
            headers={"Idempotency-Key": "test-key-002"},
            json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
        )
        assert first.status_code == 201

        mismatch = client.post(
            "/v1/restaurants/rst_001/tables/tbl_001/orders",
            headers={"Idempotency-Key": "test-key-002"},
            json={"lines": [{"itemId": "itm_001", "quantity": 2}]},
        )
        assert mismatch.status_code == 409
        assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_KEY_REPLAY_DIFFERENT_PAYLOAD"


def test_kitchen_queue_endpoint_orders_and_paginates() -> None:
    with TestClient(app) as client:
        created_order_ids: list[str] = []
        for _ in range(3):
            response = client.post(
                "/v1/restaurants/rst_001/tables/tbl_001/orders",
                json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
            )
            assert response.status_code == 201
            created_order_ids.append(response.json()["orderId"])
            time.sleep(0.01)

        first_page = client.get("/v1/restaurants/rst_001/kitchen/orders?status=PLACED&limit=2")
        assert first_page.status_code == 200
        first_payload = first_page.json()
        assert len(first_payload["orders"]) == 2
        assert first_payload["nextCursor"] is not None

        first_ids = [item["orderId"] for item in first_payload["orders"]]

        second_page = client.get(
            f"/v1/restaurants/rst_001/kitchen/orders?status=PLACED&limit=2&cursor={first_payload['nextCursor']}"
        )
        assert second_page.status_code == 200
        second_payload = second_page.json()
        second_ids = [item["orderId"] for item in second_payload["orders"]]
        assert not set(first_ids) & set(second_ids)

        all_returned = first_ids + second_ids
        for order_id in created_order_ids:
            assert order_id in all_returned
