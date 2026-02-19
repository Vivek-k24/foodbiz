from __future__ import annotations

import concurrent.futures
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app
from rop.application.ports.repositories import OptimisticConcurrencyError
from rop.domain.common.ids import OrderId
from rop.domain.order.entities import OrderStatus
from rop.infrastructure.db.repositories.order_repo import SqlAlchemyOrderRepository


def test_accept_concurrency_updates_version_once() -> None:
    with TestClient(app) as client:
        place_response = client.post(
            "/v1/restaurants/rst_001/tables/tbl_001/orders",
            json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
        )
        assert place_response.status_code == 201
        order_id = OrderId(place_response.json()["orderId"])

    repository = SqlAlchemyOrderRepository()
    order = repository.get(order_id)
    assert order is not None
    assert order.version == 1

    def _accept_once() -> str:
        try:
            updated = repository.update_status_with_version(
                order_id=order_id,
                new_status=OrderStatus.ACCEPTED,
                expected_version=1,
            )
            return updated.status.value
        except OptimisticConcurrencyError:
            return "CONFLICT"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: _accept_once(), [0, 1]))

    assert sorted(results) == ["ACCEPTED", "CONFLICT"]

    current = repository.get(order_id)
    assert current is not None
    assert current.status == OrderStatus.ACCEPTED
    assert current.version == 2
