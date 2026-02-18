from __future__ import annotations

from datetime import timezone

from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session, joinedload

from rop.application.ports.repositories import OrderRepository
from rop.domain.common.ids import MenuItemId, OrderId, OrderLineId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.order.entities import Order, OrderLine, OrderStatus
from rop.infrastructure.db.models.order import OrderLineModel, OrderModel
from rop.infrastructure.db.session import get_engine


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def add(self, order: Order) -> None:
        order_model = OrderModel(
            id=str(order.order_id),
            restaurant_id=str(order.restaurant_id),
            table_id=str(order.table_id),
            status=order.status.value,
            created_at=order.created_at,
            total_cents=order.total.amount_cents,
            currency=order.total.currency,
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
        )

    def update(self, order: Order) -> None:
        statement = (
            update(OrderModel)
            .where(OrderModel.id == str(order.order_id))
            .values(
                status=order.status.value,
                total_cents=order.total.amount_cents,
                currency=order.total.currency,
            )
        )
        with Session(self._engine) as session:
            session.execute(statement)
            session.commit()
