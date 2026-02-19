from __future__ import annotations

import base64
from datetime import datetime, timezone

from sqlalchemy import Engine, and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from rop.application.ports.repositories import (
    IdempotencyReplayMismatchError,
    InvalidCursorError,
    OptimisticConcurrencyError,
    OrderRepository,
)
from rop.domain.common.ids import MenuItemId, OrderId, OrderLineId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.order.entities import Order, OrderLine, OrderStatus
from rop.infrastructure.db.models.order import OrderLineModel, OrderModel
from rop.infrastructure.db.session import get_engine


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def add(self, order: Order) -> None:
        order_model = self._to_model(order)
        with Session(self._engine) as session:
            session.add(order_model)
            session.commit()

    def get(self, order_id: OrderId) -> Order | None:
        statement = (
            select(OrderModel)
            .options(joinedload(OrderModel.lines))
            .where(OrderModel.id == str(order_id))
            .limit(1)
        )
        with Session(self._engine) as session:
            model = session.execute(statement).unique().scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    def update(self, order: Order) -> None:
        statement = (
            update(OrderModel)
            .where(OrderModel.id == str(order.order_id))
            .values(
                status=order.status.value,
                total_cents=order.total.amount_cents,
                currency=order.total.currency,
                version=order.version,
            )
        )
        with Session(self._engine) as session:
            session.execute(statement)
            session.commit()

    def get_by_idempotency(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        key: str,
    ) -> Order | None:
        statement = (
            select(OrderModel)
            .options(joinedload(OrderModel.lines))
            .where(
                OrderModel.restaurant_id == str(restaurant_id),
                OrderModel.table_id == str(table_id),
                OrderModel.idempotency_key == key,
            )
            .limit(1)
        )
        with Session(self._engine) as session:
            model = session.execute(statement).unique().scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    def add_with_idempotency(
        self,
        order: Order,
        key: str,
        payload_hash: str,
    ) -> Order:
        statement = (
            select(OrderModel)
            .options(joinedload(OrderModel.lines))
            .where(
                OrderModel.restaurant_id == str(order.restaurant_id),
                OrderModel.table_id == str(order.table_id),
                OrderModel.idempotency_key == key,
            )
            .limit(1)
        )

        with Session(self._engine) as session:
            existing = session.execute(statement).unique().scalar_one_or_none()
            if existing is not None:
                if existing.idempotency_hash != payload_hash:
                    raise IdempotencyReplayMismatchError(
                        f"idempotency key replay with different payload: {key}"
                    )
                return self._to_domain(existing)

            model = self._to_model(order)
            model.idempotency_key = key
            model.idempotency_hash = payload_hash
            session.add(model)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.execute(statement).unique().scalar_one_or_none()
                if existing is None:
                    raise
                if existing.idempotency_hash != payload_hash:
                    raise IdempotencyReplayMismatchError(
                        f"idempotency key replay with different payload: {key}"
                    )
                return self._to_domain(existing)

        created = self.get(order.order_id)
        if created is None:
            raise RuntimeError("created order not found")
        return created

    def update_status_with_version(
        self,
        order_id: OrderId,
        new_status: OrderStatus,
        expected_version: int,
    ) -> Order:
        statement = (
            update(OrderModel)
            .where(
                OrderModel.id == str(order_id),
                OrderModel.version == expected_version,
            )
            .values(
                status=new_status.value,
                version=OrderModel.version + 1,
            )
        )
        with Session(self._engine) as session:
            result = session.execute(statement)
            if result.rowcount != 1:
                session.rollback()
                raise OptimisticConcurrencyError(f"order {order_id} version conflict")
            session.commit()

        updated = self.get(order_id)
        if updated is None:
            raise RuntimeError(f"order {order_id} not found after status update")
        return updated

    def list_for_kitchen(
        self,
        restaurant_id: RestaurantId,
        status: OrderStatus | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Order], str | None]:
        statement = (
            select(OrderModel)
            .options(joinedload(OrderModel.lines))
            .where(OrderModel.restaurant_id == str(restaurant_id))
        )
        if status is not None:
            statement = statement.where(OrderModel.status == status.value)

        cursor_parts = _decode_cursor(cursor) if cursor else None
        if cursor_parts is not None:
            cursor_created_at, cursor_order_id = cursor_parts
            statement = statement.where(
                or_(
                    OrderModel.created_at < cursor_created_at,
                    and_(
                        OrderModel.created_at == cursor_created_at,
                        OrderModel.id < cursor_order_id,
                    ),
                )
            )

        statement = statement.order_by(OrderModel.created_at.desc(), OrderModel.id.desc()).limit(
            limit + 1
        )

        with Session(self._engine) as session:
            models = list(session.execute(statement).unique().scalars().all())

        has_more = len(models) > limit
        page_models = models[:limit]
        orders = [self._to_domain(model) for model in page_models]
        next_cursor: str | None = None
        if has_more and page_models:
            last = page_models[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)
        return orders, next_cursor

    def _to_model(self, order: Order) -> OrderModel:
        order_model = OrderModel(
            id=str(order.order_id),
            restaurant_id=str(order.restaurant_id),
            table_id=str(order.table_id),
            status=order.status.value,
            version=order.version,
            created_at=order.created_at,
            total_cents=order.total.amount_cents,
            currency=order.total.currency,
            idempotency_key=order.idempotency_key,
            idempotency_hash=order.idempotency_hash,
        )
        order_model.lines = [
            OrderLineModel(
                id=str(line.line_id),
                order_id=str(order.order_id),
                item_id=str(line.item_id),
                name=line.name,
                quantity=line.quantity,
                unit_price_cents=line.unit_price.amount_cents,
                currency=line.unit_price.currency,
                line_total_cents=line.line_total.amount_cents,
                notes=line.notes,
            )
            for line in order.lines
        ]
        return order_model

    def _to_domain(self, model: OrderModel) -> Order:
        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        lines = [
            OrderLine(
                line_id=OrderLineId(line.id),
                item_id=MenuItemId(line.item_id),
                name=line.name,
                quantity=line.quantity,
                unit_price=Money(amount_cents=line.unit_price_cents, currency=line.currency),
                line_total=Money(amount_cents=line.line_total_cents, currency=line.currency),
                notes=line.notes,
            )
            for line in model.lines
        ]
        return Order(
            order_id=OrderId(model.id),
            restaurant_id=RestaurantId(model.restaurant_id),
            table_id=TableId(model.table_id),
            status=OrderStatus(model.status),
            lines=lines,
            total=Money(amount_cents=model.total_cents, currency=model.currency),
            created_at=created_at,
            version=model.version,
            idempotency_key=model.idempotency_key,
            idempotency_hash=model.idempotency_hash,
        )


def _encode_cursor(created_at: datetime, order_id: str) -> str:
    payload = f"{created_at.isoformat()}|{order_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        created_at_raw, order_id = raw.split("|", 1)
        created_at = datetime.fromisoformat(created_at_raw)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at, order_id
    except Exception as exc:
        raise InvalidCursorError("invalid cursor") from exc
