from __future__ import annotations

from fastapi import APIRouter

from rop.application.dto.responses import RolesResponse
from rop.application.use_cases.roles import ListRoles
from rop.infrastructure.db.repositories.role_repo import SqlAlchemyRoleRepository

router = APIRouter()


def _list_roles_use_case() -> ListRoles:
    return ListRoles(repository=SqlAlchemyRoleRepository())


@router.get("/v1/roles", response_model=RolesResponse)
def list_roles() -> RolesResponse:
    return _list_roles_use_case().execute()
