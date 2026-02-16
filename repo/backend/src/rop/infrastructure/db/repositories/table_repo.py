from __future__ import annotations

from datetime import timezone

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from rop.application.ports.repositories import TableRepository
from rop.domain.common.ids import RestaurantId, TableId
from rop.domain.table.entities import Table, TableStatus
from rop.infrastructure.db.models.table import TableModel
from rop.infrastructure.db.session import get_engine


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
