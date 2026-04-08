from __future__ import annotations

from rop.application.dto.responses import RolesResponse
from rop.application.mappers.foundation_mapper import to_role_response
from rop.application.ports.repositories import RoleRepository


class ListRoles:
    def __init__(self, repository: RoleRepository) -> None:
        self._repository = repository

    def execute(self) -> RolesResponse:
        return RolesResponse(
            roles=[to_role_response(role) for role in self._repository.list_roles()]
        )
