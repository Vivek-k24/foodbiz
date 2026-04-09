from __future__ import annotations

from rop.application.commerce.schemas import OrderCreateRequest, SessionCreateRequest
from rop.application.commerce.service import CommerceService
from rop.application.staff.schemas import (
    CounterOrderRequest,
    ManualOrderRequest,
    WalkInSessionRequest,
)
from rop.domain.commerce.enums import Channel, SourceType


class StaffService:
    def __init__(self, commerce: CommerceService) -> None:
        self._commerce = commerce

    def create_walk_in_session(self, request: WalkInSessionRequest):
        return self._commerce.create_session(
            SessionCreateRequest(
                restaurant_id=request.restaurant_id,
                location_id=request.location_id,
                channel=Channel.DINE_IN,
                source_type=SourceType.WAITER_ENTERED,
                table_id=request.table_id,
                metadata=request.metadata,
                expires_at=request.expires_at,
            )
        )

    def create_manual_order(self, request: ManualOrderRequest, idempotency_key: str | None):
        return self._commerce.create_order(
            OrderCreateRequest(
                restaurant_id=request.restaurant_id,
                session_id=request.session_id,
                notes=request.notes,
                lines=request.lines,
            ),
            idempotency_key=idempotency_key,
        )

    def create_counter_order(self, request: CounterOrderRequest, idempotency_key: str | None):
        session = self._commerce.create_session(
            SessionCreateRequest(
                restaurant_id=request.restaurant_id,
                location_id=request.location_id,
                channel=Channel.PICKUP,
                source_type=SourceType.COUNTER_ENTERED,
                external_reference=request.customer_reference,
                metadata=request.metadata,
            )
        )
        return self._commerce.create_order(
            OrderCreateRequest(
                restaurant_id=request.restaurant_id,
                session_id=session.id,
                notes=request.notes,
                lines=request.lines,
            ),
            idempotency_key=idempotency_key,
        )
