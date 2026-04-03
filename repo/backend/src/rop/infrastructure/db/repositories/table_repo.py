from __future__ import annotations

import base64
from datetime import datetime, timezone

from sqlalchemy import Engine, and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from rop.application.ports.repositories import (
    InvalidCursorError,
    TableOrderSummaryData,
    TableRegistryRowData,
    TableRepository,
)
from rop.domain.common.ids import RestaurantId, TableId
from rop.domain.table.entities import Table, TableStatus
from rop.infrastructure.db.models.menu import RestaurantModel
from rop.infrastructure.db.models.order import OrderModel
from rop.infrastructure.db.models.table import TableModel
from rop.infrastructure.db.session import get_engine

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class SqlAlchemyTableRepository(TableRepository):
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def get(self, table_id: TableId, restaurant_id: RestaurantId) -> Table | None:
        statement = select(TableModel).where(
            TableModel.id == str(table_id),
            TableModel.restaurant_id == str(restaurant_id),
        )
        with Session(self._engine) as session:
            model = session.execute(statement).scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    def restaurant_exists(self, restaurant_id: RestaurantId) -> bool:
        statement = (
            select(RestaurantModel.id).where(RestaurantModel.id == str(restaurant_id)).limit(1)
        )
        with Session(self._engine) as session:
            value = session.execute(statement).scalar_one_or_none()
        return value is not None

    def list_for_restaurant(
        self,
        restaurant_id: RestaurantId,
        status: TableStatus | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[TableRegistryRowData], str | None]:
        opened_sort = func.coalesce(TableModel.opened_at, _EPOCH)
        statement = select(TableModel).where(TableModel.restaurant_id == str(restaurant_id))
        if status is not None:
            statement = statement.where(TableModel.status == status.value)

        cursor_parts = _decode_cursor(cursor) if cursor else None
        if cursor_parts is not None:
            cursor_opened_at, cursor_table_id = cursor_parts
            statement = statement.where(
                or_(
                    opened_sort < cursor_opened_at,
                    and_(opened_sort == cursor_opened_at, TableModel.id < cursor_table_id),
                )
            )

        statement = statement.order_by(opened_sort.desc(), TableModel.id.desc()).limit(limit + 1)

        with Session(self._engine) as session:
            models = list(session.execute(statement).scalars().all())
            page_models = models[:limit]
            summary_by_table = self._load_summaries(
                session=session,
                restaurant_id=restaurant_id,
                table_ids=[model.id for model in page_models],
            )

        rows = [
            TableRegistryRowData(
                table=self._to_domain(model),
                summary=summary_by_table.get(model.id, _empty_table_summary()),
            )
            for model in page_models
        ]

        has_more = len(models) > limit
        next_cursor: str | None = None
        if has_more and page_models:
            last = page_models[-1]
            next_cursor = _encode_cursor(last.opened_at or _EPOCH, last.id)
        return rows, next_cursor

    def _to_domain(self, model: TableModel) -> Table:
        opened_at = model.opened_at
        closed_at = model.closed_at
        if opened_at and opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        if closed_at and closed_at.tzinfo is None:
            closed_at = closed_at.replace(tzinfo=timezone.utc)
        return Table(
            table_id=TableId(model.id),
            restaurant_id=RestaurantId(model.restaurant_id),
            status=TableStatus(model.status),
            opened_at=opened_at,
            closed_at=closed_at,
        )

    def upsert(self, table: Table) -> None:
        statement = (
            insert(TableModel)
            .values(
                id=str(table.table_id),
                restaurant_id=str(table.restaurant_id),
                status=table.status.value,
                opened_at=table.opened_at,
                closed_at=table.closed_at,
            )
            .on_conflict_do_update(
                index_elements=[TableModel.id],
                set_={
                    "restaurant_id": str(table.restaurant_id),
                    "status": table.status.value,
                    "opened_at": table.opened_at,
                    "closed_at": table.closed_at,
                },
            )
        )
        with Session(self._engine) as session:
            session.execute(statement)
            session.commit()

    def _load_summaries(
        self,
        session: Session,
        restaurant_id: RestaurantId,
        table_ids: list[str],
    ) -> dict[str, TableOrderSummaryData]:
        if not table_ids:
            return {}

        statement = (
            select(
                OrderModel.table_id,
                func.count(OrderModel.id),
                func.coalesce(func.sum(OrderModel.total_cents), 0),
                func.coalesce(func.sum(case((OrderModel.status == "PLACED", 1), else_=0)), 0),
                func.coalesce(func.sum(case((OrderModel.status == "ACCEPTED", 1), else_=0)), 0),
                func.coalesce(func.sum(case((OrderModel.status == "READY", 1), else_=0)), 0),
                func.max(OrderModel.created_at),
                func.max(OrderModel.currency),
            )
            .where(
                OrderModel.restaurant_id == str(restaurant_id),
                OrderModel.table_id.in_(table_ids),
            )
            .group_by(OrderModel.table_id)
        )

        summaries: dict[str, TableOrderSummaryData] = {}
        for row in session.execute(statement):
            last_order_at = row[6]
            if last_order_at is not None and last_order_at.tzinfo is None:
                last_order_at = last_order_at.replace(tzinfo=timezone.utc)
            summaries[row[0]] = TableOrderSummaryData(
                orders_total=int(row[1] or 0),
                amount_cents=int(row[2] or 0),
                placed=int(row[3] or 0),
                accepted=int(row[4] or 0),
                ready=int(row[5] or 0),
                last_order_at=last_order_at,
                currency=str(row[7] or "USD"),
            )
        return summaries


def _encode_cursor(opened_at: datetime, table_id: str) -> str:
    payload = f"{opened_at.isoformat()}|{table_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        opened_at_raw, table_id = raw.split("|", 1)
        opened_at = datetime.fromisoformat(opened_at_raw)
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        return opened_at, table_id
    except Exception as exc:
        raise InvalidCursorError("invalid cursor") from exc


def _empty_table_summary() -> TableOrderSummaryData:
    return TableOrderSummaryData(
        orders_total=0,
        placed=0,
        accepted=0,
        ready=0,
        amount_cents=0,
        currency="USD",
        last_order_at=None,
    )
