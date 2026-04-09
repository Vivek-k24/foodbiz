from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from rop.application.commerce.schemas import (
    LocationCreateRequest,
    LocationListResponse,
    LocationResponse,
    LocationUpdateRequest,
    OrderCreateRequest,
    OrderLineResponse,
    OrderResponse,
    OrderUpdateRequest,
    RestaurantCreateRequest,
    RestaurantListResponse,
    RestaurantResponse,
    RestaurantUpdateRequest,
    SessionCreateRequest,
    SessionResponse,
    SessionUpdateRequest,
    TableCreateRequest,
    TableResponse,
    TableSessionOpenRequest,
    TableUpdateRequest,
)
from rop.domain.commerce.enums import (
    ActorType,
    Channel,
    LocationType,
    OrderStatus,
    RestaurantStatus,
    SessionStatus,
    SourceType,
    TableStatus,
)
from rop.domain.commerce.rules import (
    can_delete_order,
    can_patch_order,
    ensure_channel_table_consistency,
    ensure_dine_in_table_ready,
    ensure_session_accepts_orders,
    ensure_third_party_metadata,
)
from rop.domain.errors import ConflictError, NotFoundError, ValidationError
from rop.infrastructure.db.models import (
    LocationModel,
    MenuItemModel,
    OrderLineModel,
    OrderModel,
    OrderStatusHistoryModel,
    RestaurantModel,
    SessionModel,
    TableModel,
)
from rop.infrastructure.messaging.redis_publisher import RedisEventPublisher


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


class CommerceService:
    def __init__(self, db: Session, publisher: RedisEventPublisher | None = None) -> None:
        self._db = db
        self._publisher = publisher or RedisEventPublisher()

    def _require_restaurant(self, restaurant_id: str) -> RestaurantModel:
        restaurant = self._db.get(RestaurantModel, restaurant_id)
        if restaurant is None or restaurant.deleted_at is not None:
            raise NotFoundError("restaurant not found", code="RESTAURANT_NOT_FOUND")
        return restaurant

    def _require_location(self, location_id: str) -> LocationModel:
        location = self._db.get(LocationModel, location_id)
        if location is None or location.deleted_at is not None:
            raise NotFoundError("location not found", code="LOCATION_NOT_FOUND")
        return location

    def _require_table(self, table_id: str) -> TableModel:
        table = self._db.get(TableModel, table_id)
        if table is None or table.deleted_at is not None:
            raise NotFoundError("table not found", code="TABLE_NOT_FOUND")
        return table

    def _require_session(self, session_id: str) -> SessionModel:
        session = self._db.get(SessionModel, session_id)
        if session is None:
            raise NotFoundError("session not found", code="SESSION_NOT_FOUND")
        return session

    def _require_order(self, order_id: str) -> OrderModel:
        order = self._db.scalar(
            select(OrderModel)
            .options(joinedload(OrderModel.lines))
            .where(OrderModel.id == order_id)
        )
        if order is None:
            raise NotFoundError("order not found", code="ORDER_NOT_FOUND")
        return order

    def _table_label(self, table_id: str | None) -> str | None:
        if not table_id:
            return None
        table = self._db.get(TableModel, table_id)
        return table.label if table else None

    def _serialize_restaurant(self, restaurant: RestaurantModel) -> RestaurantResponse:
        return RestaurantResponse(
            id=restaurant.id,
            slug=restaurant.slug,
            name=restaurant.name,
            status=RestaurantStatus(restaurant.status),
            created_at=restaurant.created_at,
            updated_at=restaurant.updated_at,
            deleted_at=restaurant.deleted_at,
        )

    def _serialize_location(self, location: LocationModel) -> LocationResponse:
        return LocationResponse(
            id=location.id,
            restaurant_id=location.restaurant_id,
            name=location.name,
            location_type=LocationType(location.location_type),
            is_active=location.is_active,
            supports_dine_in=location.supports_dine_in,
            supports_pickup=location.supports_pickup,
            supports_delivery=location.supports_delivery,
            address_line_1=location.address_line_1,
            address_line_2=location.address_line_2,
            city=location.city,
            state=location.state,
            postal_code=location.postal_code,
            country=location.country,
            created_at=location.created_at,
            updated_at=location.updated_at,
            deleted_at=location.deleted_at,
        )

    def _serialize_table(self, table: TableModel) -> TableResponse:
        return TableResponse(
            id=table.id,
            restaurant_id=table.restaurant_id,
            location_id=table.location_id,
            label=table.label,
            capacity=table.capacity,
            status=TableStatus(table.status),
            created_at=table.created_at,
            updated_at=table.updated_at,
            deleted_at=table.deleted_at,
        )

    def _serialize_session(self, session: SessionModel) -> SessionResponse:
        return SessionResponse(
            id=session.id,
            restaurant_id=session.restaurant_id,
            location_id=session.location_id,
            channel=Channel(session.channel),
            source_type=SourceType(session.source_type),
            status=SessionStatus(session.status),
            table_id=session.table_id,
            table_label=self._table_label(session.table_id),
            external_source=session.external_source,
            external_reference=session.external_reference,
            metadata=session.metadata_json,
            started_at=session.started_at,
            expires_at=session.expires_at,
            closed_at=session.closed_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def _serialize_order(self, order: OrderModel) -> OrderResponse:
        lines = [
            OrderLineResponse(
                id=line.id,
                menu_item_id=line.menu_item_id,
                item_name_snapshot=line.item_name_snapshot,
                unit_price_snapshot=_money(line.unit_price_snapshot),
                quantity=line.quantity,
                line_total=_money(line.line_total),
                notes=line.notes,
            )
            for line in order.lines
        ]
        return OrderResponse(
            id=order.id,
            restaurant_id=order.restaurant_id,
            location_id=order.location_id,
            session_id=order.session_id,
            table_id=order.table_id,
            table_label=self._table_label(order.table_id),
            channel=Channel(order.channel),
            source_type=SourceType(order.source_type),
            status=OrderStatus(order.status),
            external_source=order.external_source,
            external_reference=order.external_reference,
            subtotal=_money(order.subtotal),
            discount_total=_money(order.discount_total),
            tax_total=_money(order.tax_total),
            total=_money(order.total),
            notes=order.notes,
            idempotency_key=order.idempotency_key,
            created_at=order.created_at,
            updated_at=order.updated_at,
            deleted_at=order.deleted_at,
            lines=lines,
        )

    def _record_order_history(
        self,
        order_id: str,
        from_status: str | None,
        to_status: str,
        actor_type: ActorType,
        reason: str | None = None,
    ) -> None:
        self._db.add(
            OrderStatusHistoryModel(
                id=f"osh_{uuid4().hex[:12]}",
                order_id=order_id,
                from_status=from_status,
                to_status=to_status,
                actor_type=actor_type.value,
                actor_id=None,
                reason=reason,
            )
        )

    def _publish_order_event(self, event_type: str, order: OrderModel) -> None:
        self._publisher.publish_json(
            restaurant_id=order.restaurant_id,
            payload={
                "event_type": event_type,
                "order_id": order.id,
                "restaurant_id": order.restaurant_id,
                "location_id": order.location_id,
                "session_id": order.session_id,
                "table_id": order.table_id,
                "table_label": self._table_label(order.table_id),
                "channel": order.channel,
                "source_type": order.source_type,
                "status": order.status,
                "notes": order.notes,
                "occurred_at": _utcnow().isoformat(),
            },
        )

    def _active_session_for_table(self, table_id: str) -> SessionModel | None:
        return self._db.scalar(
            select(SessionModel).where(
                SessionModel.table_id == table_id,
                SessionModel.status == SessionStatus.OPEN.value,
            )
        )

    def _validate_location_support(self, location: LocationModel, channel: Channel) -> None:
        support_matrix = {
            Channel.DINE_IN: location.supports_dine_in,
            Channel.PICKUP: location.supports_pickup,
            Channel.DELIVERY: location.supports_delivery,
            Channel.THIRD_PARTY: location.supports_delivery,
        }
        if not support_matrix[channel]:
            raise ValidationError(
                "location does not support requested channel",
                code="CHANNEL_NOT_SUPPORTED",
                details={"channel": channel.value, "location_id": location.id},
            )

    def create_restaurant(self, request: RestaurantCreateRequest) -> RestaurantResponse:
        restaurant = RestaurantModel(
            id=f"rst_{uuid4().hex[:12]}",
            slug=request.slug.strip().lower(),
            name=request.name.strip(),
            status=request.status.value,
        )
        self._db.add(restaurant)
        self._db.commit()
        self._db.refresh(restaurant)
        return self._serialize_restaurant(restaurant)

    def list_restaurants(self) -> RestaurantListResponse:
        restaurants = self._db.scalars(
            select(RestaurantModel)
            .where(RestaurantModel.deleted_at.is_(None))
            .order_by(RestaurantModel.name.asc())
        ).all()
        return RestaurantListResponse(
            restaurants=[self._serialize_restaurant(item) for item in restaurants]
        )

    def get_restaurant(self, restaurant_id: str) -> RestaurantResponse:
        return self._serialize_restaurant(self._require_restaurant(restaurant_id))

    def update_restaurant(
        self,
        restaurant_id: str,
        request: RestaurantUpdateRequest,
    ) -> RestaurantResponse:
        restaurant = self._require_restaurant(restaurant_id)
        if request.slug is not None:
            restaurant.slug = request.slug.strip().lower()
        if request.name is not None:
            restaurant.name = request.name.strip()
        if request.status is not None:
            restaurant.status = request.status.value
        restaurant.updated_at = _utcnow()
        self._db.commit()
        self._db.refresh(restaurant)
        return self._serialize_restaurant(restaurant)

    def delete_restaurant(self, restaurant_id: str) -> RestaurantResponse:
        restaurant = self._require_restaurant(restaurant_id)
        restaurant.status = RestaurantStatus.INACTIVE.value
        restaurant.deleted_at = _utcnow()
        restaurant.updated_at = restaurant.deleted_at
        self._db.commit()
        self._db.refresh(restaurant)
        return self._serialize_restaurant(restaurant)

    def create_location(self, request: LocationCreateRequest) -> LocationResponse:
        self._require_restaurant(request.restaurant_id)
        location = LocationModel(
            id=f"loc_{uuid4().hex[:12]}",
            restaurant_id=request.restaurant_id,
            name=request.name.strip(),
            location_type=request.location_type.value,
            is_active=request.is_active,
            supports_dine_in=request.supports_dine_in,
            supports_pickup=request.supports_pickup,
            supports_delivery=request.supports_delivery,
            address_line_1=request.address_line_1,
            address_line_2=request.address_line_2,
            city=request.city,
            state=request.state,
            postal_code=request.postal_code,
            country=request.country.upper() if request.country else None,
        )
        self._db.add(location)
        self._db.commit()
        self._db.refresh(location)
        return self._serialize_location(location)

    def get_location(self, location_id: str) -> LocationResponse:
        return self._serialize_location(self._require_location(location_id))

    def list_locations(self, restaurant_id: str, channel: Channel | None) -> LocationListResponse:
        self._require_restaurant(restaurant_id)
        query = select(LocationModel).where(
            LocationModel.restaurant_id == restaurant_id,
            LocationModel.deleted_at.is_(None),
            LocationModel.is_active.is_(True),
        )
        if channel is Channel.DINE_IN:
            query = query.where(LocationModel.supports_dine_in.is_(True))
        elif channel is Channel.PICKUP:
            query = query.where(LocationModel.supports_pickup.is_(True))
        elif channel in {Channel.DELIVERY, Channel.THIRD_PARTY}:
            query = query.where(LocationModel.supports_delivery.is_(True))
        locations = self._db.scalars(query.order_by(LocationModel.name.asc())).all()
        return LocationListResponse(
            locations=[self._serialize_location(location) for location in locations]
        )

    def update_location(self, location_id: str, request: LocationUpdateRequest) -> LocationResponse:
        location = self._require_location(location_id)
        data = request.model_dump(exclude_unset=True)
        for field, value in data.items():
            if field == "location_type" and value is not None:
                setattr(location, field, value.value)
            elif field == "country" and value is not None:
                setattr(location, field, value.upper())
            else:
                setattr(location, field, value)
        location.updated_at = _utcnow()
        self._db.commit()
        self._db.refresh(location)
        return self._serialize_location(location)

    def delete_location(self, location_id: str) -> LocationResponse:
        location = self._require_location(location_id)
        open_session = self._db.scalar(
            select(SessionModel).where(
                SessionModel.location_id == location_id,
                SessionModel.status == SessionStatus.OPEN.value,
            )
        )
        if open_session is not None:
            raise ConflictError(
                "cannot delete a location with open sessions",
                code="LOCATION_HAS_OPEN_SESSIONS",
            )
        location.is_active = False
        location.deleted_at = _utcnow()
        location.updated_at = location.deleted_at
        self._db.commit()
        self._db.refresh(location)
        return self._serialize_location(location)

    def create_table(self, request: TableCreateRequest) -> TableResponse:
        self._require_restaurant(request.restaurant_id)
        if request.location_id:
            location = self._require_location(request.location_id)
            if location.restaurant_id != request.restaurant_id:
                raise ValidationError(
                    "location does not belong to restaurant",
                    code="LOCATION_RESTAURANT_MISMATCH",
                )
        table = TableModel(
            id=f"tbl_{uuid4().hex[:12]}",
            restaurant_id=request.restaurant_id,
            location_id=request.location_id,
            label=request.label.strip(),
            capacity=request.capacity,
            status=request.status.value,
        )
        self._db.add(table)
        self._db.commit()
        self._db.refresh(table)
        return self._serialize_table(table)

    def get_table(self, table_id: str) -> TableResponse:
        return self._serialize_table(self._require_table(table_id))

    def update_table(self, table_id: str, request: TableUpdateRequest) -> TableResponse:
        table = self._require_table(table_id)
        data = request.model_dump(exclude_unset=True)
        if data.get("location_id"):
            location = self._require_location(data["location_id"])
            if location.restaurant_id != table.restaurant_id:
                raise ValidationError(
                    "location does not belong to restaurant",
                    code="LOCATION_RESTAURANT_MISMATCH",
                )
        for field, value in data.items():
            if field == "status" and value is not None:
                setattr(table, field, value.value)
            elif field == "label" and value is not None:
                setattr(table, field, value.strip())
            else:
                setattr(table, field, value)
        table.updated_at = _utcnow()
        self._db.commit()
        self._db.refresh(table)
        return self._serialize_table(table)

    def delete_table(self, table_id: str) -> TableResponse:
        table = self._require_table(table_id)
        if self._active_session_for_table(table.id) is not None:
            raise ConflictError(
                "cannot delete a table with an open session",
                code="TABLE_HAS_OPEN_SESSION",
            )
        table.status = TableStatus.OUT_OF_SERVICE.value
        table.deleted_at = _utcnow()
        table.updated_at = table.deleted_at
        self._db.commit()
        self._db.refresh(table)
        return self._serialize_table(table)

    def create_session(self, request: SessionCreateRequest) -> SessionResponse:
        self._require_restaurant(request.restaurant_id)
        location = self._require_location(request.location_id)
        if location.restaurant_id != request.restaurant_id:
            raise ValidationError(
                "location does not belong to restaurant",
                code="LOCATION_RESTAURANT_MISMATCH",
            )
        ensure_channel_table_consistency(request.channel, request.table_id)
        ensure_third_party_metadata(
            request.channel,
            request.external_source,
            request.external_reference,
        )
        self._validate_location_support(location, request.channel)

        if request.table_id is not None:
            table = self._require_table(request.table_id)
            if table.restaurant_id != request.restaurant_id:
                raise ValidationError(
                    "table does not belong to restaurant",
                    code="TABLE_RESTAURANT_MISMATCH",
                )
            if table.location_id and table.location_id != location.id:
                raise ValidationError(
                    "table does not belong to location",
                    code="TABLE_LOCATION_MISMATCH",
                )
            if self._active_session_for_table(table.id) is not None:
                raise ConflictError(
                    "table already has an open session",
                    code="TABLE_SESSION_EXISTS",
                )
            ensure_dine_in_table_ready(TableStatus(table.status))
            table.status = TableStatus.OCCUPIED.value
            table.updated_at = _utcnow()

        session = SessionModel(
            id=f"ses_{uuid4().hex[:12]}",
            restaurant_id=request.restaurant_id,
            location_id=location.id,
            channel=request.channel.value,
            source_type=request.source_type.value,
            status=SessionStatus.OPEN.value,
            table_id=request.table_id,
            external_source=request.external_source,
            external_reference=request.external_reference,
            metadata_json=request.metadata,
            started_at=_utcnow(),
            expires_at=request.expires_at,
            closed_at=None,
        )
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return self._serialize_session(session)

    def open_table_session(
        self,
        table_id: str,
        request: TableSessionOpenRequest,
    ) -> SessionResponse:
        table = self._require_table(table_id)
        if table.location_id is None:
            raise ValidationError(
                "table requires a location before opening a session",
                code="TABLE_LOCATION_REQUIRED",
            )
        return self.create_session(
            SessionCreateRequest(
                restaurant_id=table.restaurant_id,
                location_id=table.location_id,
                channel=Channel.DINE_IN,
                source_type=request.source_type,
                table_id=table.id,
                external_source=request.external_source,
                external_reference=request.external_reference,
                metadata=request.metadata,
                expires_at=request.expires_at,
            )
        )

    def get_session(self, session_id: str) -> SessionResponse:
        return self._serialize_session(self._require_session(session_id))

    def update_session(self, session_id: str, request: SessionUpdateRequest) -> SessionResponse:
        session = self._require_session(session_id)
        data = request.model_dump(exclude_unset=True)
        if request.status is not None and request.status is not SessionStatus.OPEN:
            session.status = request.status.value
            if request.status in {SessionStatus.CLOSED, SessionStatus.EXPIRED}:
                session.closed_at = _utcnow()
                if session.table_id:
                    table = self._require_table(session.table_id)
                    table.status = TableStatus.AVAILABLE.value
                    table.updated_at = _utcnow()
        if "external_source" in data:
            session.external_source = request.external_source
        if "external_reference" in data:
            session.external_reference = request.external_reference
        if "metadata" in data:
            session.metadata_json = request.metadata
        if "expires_at" in data:
            session.expires_at = request.expires_at
        session.updated_at = _utcnow()
        self._db.commit()
        self._db.refresh(session)
        return self._serialize_session(session)

    def delete_session(self, session_id: str) -> SessionResponse:
        session = self._require_session(session_id)
        if session.status == SessionStatus.OPEN.value:
            session.status = SessionStatus.CLOSED.value
            session.closed_at = _utcnow()
            session.updated_at = session.closed_at
            if session.table_id:
                table = self._require_table(session.table_id)
                table.status = TableStatus.AVAILABLE.value
                table.updated_at = session.closed_at
            self._db.commit()
            self._db.refresh(session)
        return self._serialize_session(session)

    def close_table_session(self, table_id: str) -> SessionResponse:
        session = self._active_session_for_table(table_id)
        if session is None:
            raise NotFoundError("open session not found for table", code="SESSION_NOT_FOUND")
        return self.delete_session(session.id)

    def _create_order_payload_hash(self, request: OrderCreateRequest) -> str:
        payload = {
            "restaurant_id": request.restaurant_id,
            "session_id": request.session_id,
            "location_id": request.location_id,
            "table_id": request.table_id,
            "notes": request.notes,
            "lines": [line.model_dump() for line in request.lines],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def create_order(
        self,
        request: OrderCreateRequest,
        idempotency_key: str | None,
    ) -> OrderResponse:
        self._require_restaurant(request.restaurant_id)
        session = self._require_session(request.session_id)
        if session.restaurant_id != request.restaurant_id:
            raise ValidationError(
                "session does not belong to restaurant",
                code="SESSION_RESTAURANT_MISMATCH",
            )
        ensure_session_accepts_orders(SessionStatus(session.status))
        ensure_channel_table_consistency(Channel(session.channel), session.table_id)
        ensure_third_party_metadata(
            Channel(session.channel),
            session.external_source,
            session.external_reference,
        )

        if request.table_id is not None and request.table_id != session.table_id:
            raise ValidationError(
                "table_id does not match session",
                code="TABLE_SESSION_MISMATCH",
            )
        if request.location_id is not None and request.location_id != session.location_id:
            raise ValidationError(
                "location_id does not match session",
                code="LOCATION_SESSION_MISMATCH",
            )

        table: TableModel | None = None
        if session.table_id:
            table = self._require_table(session.table_id)
            ensure_dine_in_table_ready(TableStatus(table.status))

        normalized_key = (
            idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None
        )
        payload_hash = self._create_order_payload_hash(request)
        if normalized_key:
            existing = self._db.scalar(
                select(OrderModel)
                .options(joinedload(OrderModel.lines))
                .where(
                    OrderModel.restaurant_id == request.restaurant_id,
                    OrderModel.idempotency_key == normalized_key,
                )
            )
            if existing is not None:
                if existing.idempotency_hash != payload_hash:
                    raise ConflictError(
                        "idempotency key was already used with a different payload",
                        code="IDEMPOTENCY_KEY_REPLAY_DIFFERENT_PAYLOAD",
                    )
                return self._serialize_order(existing)

        menu_item_ids = [line.menu_item_id for line in request.lines]
        menu_items = self._db.scalars(
            select(MenuItemModel).where(MenuItemModel.id.in_(menu_item_ids))
        ).all()
        items_by_id = {item.id: item for item in menu_items}

        line_models: list[OrderLineModel] = []
        subtotal = Decimal("0.00")
        for line in request.lines:
            menu_item = items_by_id.get(line.menu_item_id)
            if menu_item is None or menu_item.deleted_at is not None or not menu_item.is_available:
                raise ValidationError(
                    f"menu item '{line.menu_item_id}' is unavailable",
                    code="MENU_ITEM_UNAVAILABLE",
                )
            quantity = Decimal(line.quantity)
            line_total = menu_item.price * quantity
            subtotal += line_total
            line_models.append(
                OrderLineModel(
                    id=f"orl_{uuid4().hex[:12]}",
                    menu_item_id=menu_item.id,
                    item_name_snapshot=menu_item.name,
                    unit_price_snapshot=menu_item.price,
                    quantity=line.quantity,
                    line_total=line_total,
                    notes=line.notes,
                )
            )

        order = OrderModel(
            id=f"ord_{uuid4().hex[:12]}",
            restaurant_id=request.restaurant_id,
            location_id=session.location_id,
            session_id=session.id,
            table_id=session.table_id,
            channel=session.channel,
            source_type=session.source_type,
            status=OrderStatus.PENDING.value,
            external_source=session.external_source,
            external_reference=session.external_reference,
            subtotal=subtotal,
            discount_total=Decimal("0.00"),
            tax_total=Decimal("0.00"),
            total=subtotal,
            notes=request.notes,
            idempotency_key=normalized_key,
            idempotency_hash=payload_hash if normalized_key else None,
            lines=line_models,
        )
        self._db.add(order)
        self._record_order_history(order.id, None, OrderStatus.PENDING.value, ActorType.SYSTEM)
        if table is not None and table.status == TableStatus.AVAILABLE.value:
            table.status = TableStatus.OCCUPIED.value
            table.updated_at = _utcnow()
        self._db.commit()
        self._db.refresh(order)
        order = self._require_order(order.id)
        self._publish_order_event("order.created", order)
        return self._serialize_order(order)

    def get_order(self, order_id: str) -> OrderResponse:
        return self._serialize_order(self._require_order(order_id))

    def update_order(self, order_id: str, request: OrderUpdateRequest) -> OrderResponse:
        order = self._require_order(order_id)
        if not can_patch_order(OrderStatus(order.status)):
            raise ConflictError(
                "order can no longer be edited",
                code="ORDER_UPDATE_NOT_ALLOWED",
            )
        if request.notes is not None:
            order.notes = request.notes
        order.updated_at = _utcnow()
        self._db.commit()
        self._db.refresh(order)
        order = self._require_order(order.id)
        return self._serialize_order(order)

    def delete_order(self, order_id: str) -> OrderResponse:
        order = self._require_order(order_id)
        if not can_delete_order(OrderStatus(order.status)):
            raise ConflictError(
                "order can only be canceled before kitchen work starts",
                code="ORDER_DELETE_NOT_ALLOWED",
            )
        order.deleted_at = _utcnow()
        order.updated_at = order.deleted_at
        order.status = OrderStatus.CANCELED.value
        self._record_order_history(
            order.id,
            OrderStatus.PENDING.value,
            OrderStatus.CANCELED.value,
            ActorType.STAFF,
            reason="deleted via API",
        )
        self._db.commit()
        self._db.refresh(order)
        order = self._require_order(order.id)
        self._publish_order_event("order.canceled", order)
        return self._serialize_order(order)
