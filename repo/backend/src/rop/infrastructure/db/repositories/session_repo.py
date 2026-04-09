from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as OrmSession

from rop.application.ports.repositories import SessionRepository
from rop.domain.common.ids import LocationId, RestaurantId, RoleId, SessionId
from rop.domain.session.entities import Session, SessionStatus
from rop.infrastructure.db.models.session_record import SessionModel
from rop.infrastructure.db.session import get_engine


class SqlAlchemySessionRepository(SessionRepository):
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def open_session(
        self,
        restaurant_id: RestaurantId,
        location_id: LocationId,
        opened_by_role_id: RoleId | None,
        opened_by_source: str | None,
        notes: str | None,
    ) -> Session:
        with OrmSession(self._engine) as session:
            existing = session.execute(
                select(SessionModel)
                .where(
                    SessionModel.restaurant_id == str(restaurant_id),
                    SessionModel.location_id == str(location_id),
                    SessionModel.status == SessionStatus.OPEN.value,
                )
                .order_by(SessionModel.opened_at.desc(), SessionModel.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            if existing is not None:
                return self._to_domain(existing)

            model = SessionModel(
                id=f"ses_{uuid4().hex[:12]}",
                restaurant_id=str(restaurant_id),
                location_id=str(location_id),
                status=SessionStatus.OPEN.value,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
                opened_by_role_id=str(opened_by_role_id) if opened_by_role_id else None,
                opened_by_source=opened_by_source,
                notes=notes,
            )
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_domain(model)

    def create_internal_session(
        self,
        restaurant_id: RestaurantId,
        location_id: LocationId,
        opened_by_source: str | None,
        notes: str | None,
    ) -> Session:
        with OrmSession(self._engine) as session:
            model = SessionModel(
                id=f"ses_{uuid4().hex[:12]}",
                restaurant_id=str(restaurant_id),
                location_id=str(location_id),
                status=SessionStatus.OPEN.value,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
                opened_by_role_id=None,
                opened_by_source=opened_by_source,
                notes=notes,
            )
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_domain(model)

    def close_session(self, session_id: SessionId) -> Session | None:
        with OrmSession(self._engine) as session:
            model = session.execute(
                select(SessionModel).where(SessionModel.id == str(session_id)).limit(1)
            ).scalar_one_or_none()
            if model is None:
                return None
            if model.status == SessionStatus.OPEN.value:
                model.status = SessionStatus.CLOSED.value
                model.closed_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(model)
            return self._to_domain(model)

    def get_session(self, session_id: SessionId) -> Session | None:
        with OrmSession(self._engine) as session:
            model = session.execute(
                select(SessionModel).where(SessionModel.id == str(session_id)).limit(1)
            ).scalar_one_or_none()
        return self._to_domain(model) if model is not None else None

    def get_active_for_location(
        self,
        restaurant_id: RestaurantId,
        location_id: LocationId,
    ) -> Session | None:
        statement = (
            select(SessionModel)
            .where(
                SessionModel.restaurant_id == str(restaurant_id),
                SessionModel.location_id == str(location_id),
                SessionModel.status == SessionStatus.OPEN.value,
            )
            .order_by(SessionModel.opened_at.desc(), SessionModel.id.desc())
            .limit(1)
        )
        with OrmSession(self._engine) as session:
            model = session.execute(statement).scalar_one_or_none()
        return self._to_domain(model) if model is not None else None

    def list_sessions(
        self,
        restaurant_id: RestaurantId,
        location_id: LocationId | None,
        status: SessionStatus | None,
    ) -> list[Session]:
        statement = select(SessionModel).where(SessionModel.restaurant_id == str(restaurant_id))
        if location_id is not None:
            statement = statement.where(SessionModel.location_id == str(location_id))
        if status is not None:
            statement = statement.where(SessionModel.status == status.value)
        statement = statement.order_by(SessionModel.opened_at.desc(), SessionModel.id.desc())
        with OrmSession(self._engine) as session:
            models = list(session.execute(statement).scalars().all())
        return [self._to_domain(model) for model in models]

    def _to_domain(self, model: SessionModel) -> Session:
        opened_at = model.opened_at
        closed_at = model.closed_at
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        if closed_at is not None and closed_at.tzinfo is None:
            closed_at = closed_at.replace(tzinfo=timezone.utc)
        return Session(
            session_id=SessionId(model.id),
            restaurant_id=RestaurantId(model.restaurant_id),
            location_id=LocationId(model.location_id),
            status=SessionStatus(model.status),
            opened_at=opened_at,
            closed_at=closed_at,
            opened_by_role_id=RoleId(model.opened_by_role_id) if model.opened_by_role_id else None,
            opened_by_source=model.opened_by_source,
            notes=model.notes,
        )
