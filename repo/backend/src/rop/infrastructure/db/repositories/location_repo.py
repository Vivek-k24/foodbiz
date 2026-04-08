from __future__ import annotations

from datetime import timezone

from sqlalchemy import Engine, exists, select
from sqlalchemy.orm import Session

from rop.application.ports.repositories import LocationRepository, LocationRowData
from rop.domain.common.ids import LocationId, RestaurantId, SessionId
from rop.domain.location.entities import Location, LocationType
from rop.domain.session.entities import SessionStatus
from rop.infrastructure.db.models.location import LocationModel
from rop.infrastructure.db.models.session_record import SessionModel
from rop.infrastructure.db.session import get_engine


class SqlAlchemyLocationRepository(LocationRepository):
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def list_for_restaurant(
        self,
        restaurant_id: RestaurantId,
        location_type: LocationType | None,
        is_active: bool | None,
        session_status: SessionStatus | None,
    ) -> list[LocationRowData]:
        statement = select(LocationModel).where(LocationModel.restaurant_id == str(restaurant_id))
        if location_type is not None:
            statement = statement.where(LocationModel.type == location_type.value)
        if is_active is not None:
            statement = statement.where(LocationModel.is_active == is_active)
        if session_status is not None:
            status_exists = exists(
                select(SessionModel.id).where(
                    SessionModel.restaurant_id == str(restaurant_id),
                    SessionModel.location_id == LocationModel.id,
                    SessionModel.status == session_status.value,
                )
            )
            statement = statement.where(status_exists)
        statement = statement.order_by(LocationModel.type.asc(), LocationModel.name.asc())

        with Session(self._engine) as session:
            models = list(session.execute(statement).scalars().all())
            rows: list[LocationRowData] = []
            for model in models:
                active_session = session.execute(
                    select(SessionModel)
                    .where(
                        SessionModel.restaurant_id == str(restaurant_id),
                        SessionModel.location_id == model.id,
                        SessionModel.status == SessionStatus.OPEN.value,
                    )
                    .order_by(SessionModel.opened_at.desc(), SessionModel.id.desc())
                    .limit(1)
                ).scalar_one_or_none()

                rows.append(
                    LocationRowData(
                        location=self._to_domain(model),
                        session_status=SessionStatus.OPEN if active_session else None,
                        active_session_id=SessionId(active_session.id) if active_session else None,
                        last_session_opened_at=(
                            active_session.opened_at.replace(tzinfo=timezone.utc)
                            if active_session and active_session.opened_at.tzinfo is None
                            else active_session.opened_at if active_session else None
                        ),
                    )
                )
        return rows

    def get_location(self, restaurant_id: RestaurantId, location_id: LocationId) -> Location | None:
        statement = (
            select(LocationModel)
            .where(
                LocationModel.restaurant_id == str(restaurant_id),
                LocationModel.id == str(location_id),
            )
            .limit(1)
        )
        with Session(self._engine) as session:
            model = session.execute(statement).scalar_one_or_none()
        return self._to_domain(model) if model is not None else None

    def _to_domain(self, model: LocationModel) -> Location:
        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return Location(
            location_id=LocationId(model.id),
            restaurant_id=RestaurantId(model.restaurant_id),
            location_type=LocationType(model.type),
            name=model.name,
            display_label=model.display_label,
            capacity=model.capacity,
            zone=model.zone,
            is_active=model.is_active,
            created_at=created_at,
        )
