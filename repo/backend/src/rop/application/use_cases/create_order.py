from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from rop.application.dto.requests import (
    CreateOrderRequest,
    PlaceOrderLineModifierRequest,
)
from rop.application.dto.responses import OrderResponse
from rop.application.mappers.event_envelope import serialize_order_event
from rop.application.mappers.order_mapper import to_order_response
from rop.application.metrics.order_lifecycle import record_order_status
from rop.application.ports.publisher import EventPublisher
from rop.application.ports.repositories import (
    IdempotencyReplayMismatchError as RepoIdempotencyReplayMismatchError,
)
from rop.application.ports.repositories import (
    LocationRepository,
    OrderEventRecord,
    OrderRepository,
    SessionRepository,
)
from rop.application.use_cases.context import TraceContext
from rop.domain.common.ids import (
    LocationId,
    OrderEventId,
    OrderId,
    OrderLineId,
    RestaurantId,
    SessionId,
    TableId,
)
from rop.domain.common.location_keys import table_id_from_location
from rop.domain.common.money import Money
from rop.domain.location.entities import LocationType
from rop.domain.menu.entities import AllowedModifier, MenuItem
from rop.domain.order.entities import OrderLine, OrderSource, create_placed_order
from rop.domain.order.events import OrderPlaced
from rop.domain.order.value_objects import OrderLineModifier
from rop.domain.session.entities import SessionStatus


class LocationNotFoundError(Exception):
    pass


class SessionRequiredError(Exception):
    pass


class MenuNotFoundError(Exception):
    pass


class MenuItemUnavailableError(Exception):
    pass


class IdempotencyReplayMismatchError(Exception):
    pass


class InvalidModifierError(Exception):
    pass


class InvalidModifierValueError(Exception):
    pass


class InvalidOrderSourceError(Exception):
    pass


class CreateOrder:
    def __init__(
        self,
        menu_repository,
        location_repository: LocationRepository,
        session_repository: SessionRepository,
        order_repository: OrderRepository,
        publisher: EventPublisher,
    ) -> None:
        self._menu_repository = menu_repository
        self._location_repository = location_repository
        self._session_repository = session_repository
        self._order_repository = order_repository
        self._publisher = publisher

    def execute(
        self,
        request_dto: CreateOrderRequest,
        trace_ctx: TraceContext,
        idempotency_key: str | None = None,
    ) -> OrderResponse:
        restaurant_id = RestaurantId(request_dto.restaurant_id)
        location_id = LocationId(request_dto.location_id)
        source = _validated_order_source(request_dto.source)
        location = self._location_repository.get_location(restaurant_id, location_id)
        if location is None:
            raise LocationNotFoundError(f"location {location_id} not found")

        table_id = _resolve_table_id(request_dto.table_id, location_id)
        session_id = SessionId(request_dto.session_id) if request_dto.session_id else None
        if session_id is None:
            active_session = self._session_repository.get_active_for_location(
                restaurant_id=restaurant_id,
                location_id=location_id,
            )
            if active_session is not None and active_session.status == SessionStatus.OPEN:
                session_id = active_session.session_id

        if (
            location.location_type in {LocationType.TABLE, LocationType.BAR_SEAT}
            and session_id is None
        ):
            raise SessionRequiredError(
                f"location {location_id} requires an open session before ordering"
            )

        menu = self._menu_repository.get_menu_by_restaurant_id(restaurant_id)
        if menu is None:
            raise MenuNotFoundError(f"menu not found for restaurant_id={restaurant_id}")

        menu_items = {str(item.item_id): item for item in menu.items}
        order_lines: list[OrderLine] = []
        for request_line in request_dto.lines:
            if request_line.quantity < 1:
                raise MenuItemUnavailableError("quantity must be >= 1")

            menu_item = menu_items.get(request_line.item_id)
            if menu_item is None:
                raise MenuItemUnavailableError(f"menu item {request_line.item_id} does not exist")
            if not menu_item.is_available:
                raise MenuItemUnavailableError(f"menu item {request_line.item_id} is unavailable")

            unit_price = menu_item.price_money
            line_total = Money(
                amount_cents=unit_price.amount_cents * request_line.quantity,
                currency=unit_price.currency,
            )
            order_lines.append(
                OrderLine(
                    line_id=OrderLineId(f"orl_{uuid4().hex[:12]}"),
                    item_id=menu_item.item_id,
                    name=menu_item.name,
                    quantity=request_line.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    notes=request_line.notes,
                    modifiers=_validated_modifiers(menu_item, request_line.modifiers),
                )
            )

        now = datetime.now(timezone.utc)
        payload_hash = _request_hash(request_dto)
        order = create_placed_order(
            order_id=OrderId(f"ord_{uuid4().hex[:12]}"),
            restaurant_id=restaurant_id,
            location_id=location_id,
            table_id=table_id,
            session_id=session_id,
            source=source,
            lines=order_lines,
            now=now,
            idempotency_key=idempotency_key,
            idempotency_hash=payload_hash if idempotency_key else None,
        )
        created = True
        persisted_order = order
        if idempotency_key and table_id is not None:
            try:
                persisted_order = self._order_repository.add_with_idempotency(
                    order=order,
                    key=idempotency_key,
                    payload_hash=payload_hash,
                )
            except RepoIdempotencyReplayMismatchError as exc:
                raise IdempotencyReplayMismatchError(str(exc)) from exc
            created = persisted_order.order_id == order.order_id
        else:
            self._order_repository.add(order)

        if created:
            persisted_location_id = persisted_order.location_id
            assert persisted_location_id is not None
            event = OrderPlaced(
                order_id=persisted_order.order_id,
                restaurant_id=persisted_order.restaurant_id,
                location_id=persisted_location_id,
                table_id=persisted_order.table_id,
                session_id=persisted_order.session_id,
                source=persisted_order.source,
                total=persisted_order.total,
                created_at=persisted_order.created_at,
            )
            append_event = getattr(self._order_repository, "append_event", None)
            if callable(append_event):
                append_event(
                    OrderEventRecord(
                        event_id=OrderEventId(f"evt_{uuid4().hex[:12]}"),
                        order_id=persisted_order.order_id,
                        restaurant_id=persisted_order.restaurant_id,
                        location_id=persisted_location_id,
                        session_id=persisted_order.session_id,
                        event_type="ORDER_PLACED",
                        order_status_after=persisted_order.status,
                        triggered_by_source=persisted_order.source,
                        created_at=event.created_at,
                        metadata={
                            "request_id": trace_ctx.request_id,
                            "trace_id": trace_ctx.trace_id,
                            "table_id": str(persisted_order.table_id)
                            if persisted_order.table_id is not None
                            else None,
                        },
                    )
                )
            message = serialize_order_event(
                event_type="order.placed",
                occurred_at=event.created_at,
                order=persisted_order,
                trace_id=trace_ctx.trace_id,
                request_id=trace_ctx.request_id,
            )
            record_order_status(persisted_order)
            try:
                self._publisher.publish(channel=f"events:{restaurant_id}", message=message)
            except Exception:
                pass

        return to_order_response(persisted_order)


def _resolve_table_id(raw_table_id: str | None, location_id: LocationId) -> TableId | None:
    if raw_table_id:
        return TableId(raw_table_id)
    return table_id_from_location(location_id)


def _request_hash(request_dto: CreateOrderRequest) -> str:
    normalized_payload = request_dto.model_dump(mode="json", by_alias=True, exclude_none=False)
    canonical = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validated_order_source(raw_source: str | None) -> OrderSource:
    if raw_source is None:
        raise InvalidOrderSourceError("source is required")
    try:
        return OrderSource(raw_source)
    except ValueError as exc:
        raise InvalidOrderSourceError(f"invalid order source: {raw_source}") from exc


def _validated_modifiers(
    menu_item: MenuItem,
    request_modifiers: list[PlaceOrderLineModifierRequest] | None,
) -> list[OrderLineModifier]:
    allowed_by_code = {modifier.code: modifier for modifier in menu_item.allowed_modifiers}
    selected_modifiers: list[OrderLineModifier] = []
    seen_codes: set[str] = set()

    for request_modifier in request_modifiers or []:
        code = request_modifier.code.strip()
        if not code:
            raise InvalidModifierError("modifier code must be non-empty")
        if code in seen_codes:
            raise InvalidModifierError(
                f"modifier {code} was provided more than once for item {menu_item.item_id}"
            )
        seen_codes.add(code)

        allowed_modifier = allowed_by_code.get(code)
        if allowed_modifier is None:
            raise InvalidModifierError(
                f"modifier {code} is not allowed for item {menu_item.item_id}"
            )

        selected_modifiers.append(
            OrderLineModifier(
                code=allowed_modifier.code,
                label=allowed_modifier.label,
                value=_validated_modifier_value(allowed_modifier, request_modifier.value),
            )
        )

    return selected_modifiers


def _validated_modifier_value(allowed_modifier: AllowedModifier, raw_value: str) -> str:
    if allowed_modifier.kind == "toggle":
        if raw_value not in {"true", "false"}:
            raise InvalidModifierValueError(
                f"modifier {allowed_modifier.code} must be 'true' or 'false'"
            )
        return raw_value

    if allowed_modifier.kind == "choice":
        if raw_value not in allowed_modifier.options:
            raise InvalidModifierValueError(
                f"modifier {allowed_modifier.code} must be one of {allowed_modifier.options}"
            )
        return raw_value

    normalized_value = raw_value.strip()
    if not normalized_value or len(normalized_value) > 80:
        raise InvalidModifierValueError(
            f"modifier {allowed_modifier.code} text must be between 1 and 80 characters"
        )
    return normalized_value
