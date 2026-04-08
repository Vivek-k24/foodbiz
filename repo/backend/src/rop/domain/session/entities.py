from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from rop.domain.common.ids import LocationId, RestaurantId, RoleId, SessionId


class SessionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Session:
    session_id: SessionId
    restaurant_id: RestaurantId
    location_id: LocationId
    status: SessionStatus
    opened_at: datetime
    closed_at: datetime | None
    opened_by_role_id: RoleId | None
    opened_by_source: str | None
    notes: str | None

    def __post_init__(self) -> None:
        if self.status == SessionStatus.CLOSED and self.closed_at is None:
            raise ValueError("closed sessions must define closed_at")

    def close(self, now: datetime) -> Session:
        if self.status == SessionStatus.CLOSED:
            return self
        return Session(
            session_id=self.session_id,
            restaurant_id=self.restaurant_id,
            location_id=self.location_id,
            status=SessionStatus.CLOSED,
            opened_at=self.opened_at,
            closed_at=now,
            opened_by_role_id=self.opened_by_role_id,
            opened_by_source=self.opened_by_source,
            notes=self.notes,
        )
