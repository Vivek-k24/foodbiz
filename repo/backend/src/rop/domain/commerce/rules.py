from __future__ import annotations

from rop.domain.commerce.enums import Channel, OrderStatus, SessionStatus, TableStatus
from rop.domain.errors import ConflictError, ValidationError


def ensure_channel_table_consistency(channel: Channel, table_id: str | None) -> None:
    if channel is Channel.DINE_IN and not table_id:
        raise ValidationError(
            "dine_in workflows require table_id",
            code="TABLE_REQUIRED",
            details={"channel": channel.value},
        )
    if channel is not Channel.DINE_IN and table_id is not None:
        raise ValidationError(
            "table_id is only valid for dine_in workflows",
            code="TABLE_NOT_ALLOWED",
            details={"channel": channel.value},
        )


def ensure_third_party_metadata(
    channel: Channel,
    external_source: str | None,
    external_reference: str | None,
) -> None:
    if channel is Channel.THIRD_PARTY and not external_reference:
        raise ValidationError(
            "third_party workflows require external_reference",
            code="EXTERNAL_REFERENCE_REQUIRED",
            details={"channel": channel.value},
        )


def ensure_session_accepts_orders(status: SessionStatus) -> None:
    if status is SessionStatus.CLOSED:
        raise ConflictError(
            "closed sessions cannot accept new orders",
            code="SESSION_CLOSED",
        )
    if status is SessionStatus.EXPIRED:
        raise ConflictError(
            "expired sessions cannot accept new orders",
            code="SESSION_EXPIRED",
        )


def ensure_dine_in_table_ready(table_status: TableStatus) -> None:
    if table_status not in {TableStatus.AVAILABLE, TableStatus.OCCUPIED}:
        raise ConflictError(
            "table is not available for ordering",
            code="TABLE_NOT_READY",
            details={"table_status": table_status.value},
        )


def can_delete_order(status: OrderStatus) -> bool:
    return status is OrderStatus.PENDING


def can_patch_order(status: OrderStatus) -> bool:
    return status in {
        OrderStatus.PENDING,
        OrderStatus.ACCEPTED,
        OrderStatus.READY,
        OrderStatus.SERVED,
    }
