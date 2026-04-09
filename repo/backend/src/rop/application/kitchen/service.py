from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from rop.application.commerce.schemas import OrderResponse
from rop.application.commerce.service import CommerceService
from rop.application.kitchen.schemas import KitchenQueueEntryResponse, KitchenQueueResponse
from rop.domain.commerce.enums import ActorType, Channel, OrderStatus, SourceType
from rop.domain.kitchen.workflow import apply_action
from rop.infrastructure.db.models import OrderModel, TableModel
from rop.infrastructure.messaging.redis_publisher import RedisEventPublisher


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KitchenService:
    def __init__(self, db: Session, publisher: RedisEventPublisher | None = None) -> None:
        self._db = db
        self._commerce = CommerceService(db=db, publisher=publisher)

    def queue(
        self, restaurant_id: str, status: OrderStatus | None, limit: int
    ) -> KitchenQueueResponse:
        query = (
            select(OrderModel)
            .where(
                OrderModel.restaurant_id == restaurant_id,
                OrderModel.deleted_at.is_(None),
            )
            .order_by(OrderModel.created_at.asc())
            .limit(limit)
        )
        if status is not None:
            query = query.where(OrderModel.status == status.value)
        else:
            query = query.where(
                OrderModel.status.in_(
                    [
                        OrderStatus.PENDING.value,
                        OrderStatus.ACCEPTED.value,
                        OrderStatus.READY.value,
                    ]
                )
            )

        orders = self._db.scalars(query).all()
        entries: list[KitchenQueueEntryResponse] = []
        now = _utcnow()
        for order in orders:
            table_label = None
            if order.table_id:
                table = self._db.get(TableModel, order.table_id)
                table_label = table.label if table else None
            entries.append(
                KitchenQueueEntryResponse(
                    id=order.id,
                    restaurant_id=order.restaurant_id,
                    location_id=order.location_id,
                    session_id=order.session_id,
                    table_id=order.table_id,
                    table_label=table_label,
                    channel=Channel(order.channel),
                    source_type=SourceType(order.source_type),
                    status=OrderStatus(order.status),
                    notes=order.notes,
                    age_seconds=max(0, int((now - order.created_at).total_seconds())),
                    created_at=order.created_at,
                    updated_at=order.updated_at,
                )
            )
        return KitchenQueueResponse(orders=entries)

    def transition(self, order_id: str, action: str) -> OrderResponse:
        order = self._commerce._require_order(order_id)
        current_status = OrderStatus(order.status)
        next_status = apply_action(current_status, action)
        order.status = next_status.value
        order.updated_at = _utcnow()
        actor_type = ActorType.KITCHEN if action in {"accept", "ready"} else ActorType.STAFF
        self._commerce._record_order_history(
            order.id,
            current_status.value,
            next_status.value,
            actor_type,
        )
        self._db.commit()
        self._db.refresh(order)
        order = self._commerce._require_order(order.id)
        event_type = {
            "accept": "order.accepted",
            "ready": "order.ready",
            "served": "order.served",
            "settled": "order.settled",
        }[action]
        self._commerce._publish_order_event(event_type, order)
        return self._commerce._serialize_order(order)
