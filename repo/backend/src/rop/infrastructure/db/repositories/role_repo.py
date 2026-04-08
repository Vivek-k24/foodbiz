from __future__ import annotations

from datetime import timezone

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from rop.application.ports.repositories import RoleRepository
from rop.domain.common.ids import RoleId
from rop.domain.role.entities import RoleDefinition
from rop.infrastructure.db.models.role import RoleModel
from rop.infrastructure.db.session import get_engine


class SqlAlchemyRoleRepository(RoleRepository):
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def list_roles(self) -> list[RoleDefinition]:
        statement = select(RoleModel).order_by(RoleModel.role_group.asc(), RoleModel.code.asc())
        with Session(self._engine) as session:
            models = list(session.execute(statement).scalars().all())

        roles: list[RoleDefinition] = []
        for model in models:
            created_at = model.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            roles.append(
                RoleDefinition(
                    role_id=RoleId(model.id),
                    code=model.code,
                    display_name=model.display_name,
                    role_group=model.role_group,
                    created_at=created_at,
                )
            )
        return roles
