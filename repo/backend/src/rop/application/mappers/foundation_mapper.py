from __future__ import annotations

from rop.application.dto.responses import (
    LocationResponse,
    OrderEventResponse,
    RestaurantResponse,
    RoleResponse,
    SessionResponse,
)
from rop.application.ports.repositories import LocationRowData, OrderEventRecord
from rop.domain.restaurant.entities import Restaurant
from rop.domain.role.entities import RoleDefinition
from rop.domain.session.entities import Session


def to_restaurant_response(restaurant: Restaurant) -> RestaurantResponse:
    return RestaurantResponse(
        restaurantId=str(restaurant.restaurant_id),
        name=restaurant.name,
        timezone=restaurant.timezone,
        currency=restaurant.currency,
        createdAt=restaurant.created_at,
    )


def to_location_response(row: LocationRowData) -> LocationResponse:
    location = row.location
    return LocationResponse(
        locationId=str(location.location_id),
        restaurantId=str(location.restaurant_id),
        type=location.location_type.value,
        name=location.name,
        displayLabel=location.display_label,
        capacity=location.capacity,
        zone=location.zone,
        isActive=location.is_active,
        createdAt=location.created_at,
        sessionStatus=row.session_status.value if row.session_status is not None else None,
        activeSessionId=str(row.active_session_id) if row.active_session_id is not None else None,
        lastSessionOpenedAt=row.last_session_opened_at,
    )


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        sessionId=str(session.session_id),
        restaurantId=str(session.restaurant_id),
        locationId=str(session.location_id),
        status=session.status.value,
        openedAt=session.opened_at,
        closedAt=session.closed_at,
        openedByRoleId=str(session.opened_by_role_id) if session.opened_by_role_id else None,
        openedBySource=session.opened_by_source,
        notes=session.notes,
    )


def to_role_response(role: RoleDefinition) -> RoleResponse:
    return RoleResponse(
        roleId=str(role.role_id),
        code=role.code,
        displayName=role.display_name,
        roleGroup=role.role_group,
        createdAt=role.created_at,
    )


def to_order_event_response(event: OrderEventRecord) -> OrderEventResponse:
    return OrderEventResponse(
        eventId=str(event.event_id),
        orderId=str(event.order_id),
        restaurantId=str(event.restaurant_id),
        locationId=str(event.location_id),
        sessionId=str(event.session_id) if event.session_id is not None else None,
        eventType=event.event_type,
        orderStatusAfter=event.order_status_after.value,
        triggeredBySource=event.triggered_by_source.value,
        createdAt=event.created_at,
        metadata=event.metadata,
    )
