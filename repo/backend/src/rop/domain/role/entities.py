from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rop.domain.common.ids import RoleId


@dataclass(frozen=True)
class RoleDefinition:
    role_id: RoleId
    code: str
    display_name: str
    role_group: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("role code must be non-empty")
        if not self.display_name.strip():
            raise ValueError("role display_name must be non-empty")
        if not self.role_group.strip():
            raise ValueError("role_group must be non-empty")
