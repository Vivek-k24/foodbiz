from __future__ import annotations

from datetime import timezone

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from rop.application.ports.repositories import RestaurantRepository
from rop.domain.common.ids import RestaurantId
from rop.domain.restaurant.entities import Restaurant
from rop.infrastructure.db.models.menu import RestaurantModel
from rop.infrastructure.db.session import get_engine


class SqlAlchemyRestaurantRepository(RestaurantRepository):
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def list_restaurants(self) -> list[Restaurant]:
        statement = select(RestaurantModel).order_by(RestaurantModel.id.asc())
        with Session(self._engine) as session:
            models = list(session.execute(statement).scalars().all())
        return [self._to_domain(model) for model in models]

    def get_restaurant(self, restaurant_id: RestaurantId) -> Restaurant | None:
        statement = select(RestaurantModel).where(RestaurantModel.id == str(restaurant_id)).limit(1)
        with Session(self._engine) as session:
            model = session.execute(statement).scalar_one_or_none()
        return self._to_domain(model) if model is not None else None

    def _to_domain(self, model: RestaurantModel) -> Restaurant:
        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return Restaurant(
            restaurant_id=RestaurantId(model.id),
            name=model.name,
            timezone=model.timezone,
            currency=model.currency,
            created_at=created_at,
        )
