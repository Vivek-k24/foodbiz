from __future__ import annotations

from enum import StrEnum


class Channel(StrEnum):
    DINE_IN = "dine_in"
    PICKUP = "pickup"
    DELIVERY = "delivery"
    THIRD_PARTY = "third_party"


class SourceType(StrEnum):
    QR = "qr"
    BUSINESS_WEBSITE = "business_website"
    WAITER_ENTERED = "waiter_entered"
    COUNTER_ENTERED = "counter_entered"
    UBER_EATS = "uber_eats"
    DOORDASH = "doordash"


class SessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    EXPIRED = "expired"


class TableStatus(StrEnum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    OUT_OF_SERVICE = "out_of_service"


class OrderStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    READY = "ready"
    SERVED = "served"
    SETTLED = "settled"
    CANCELED = "canceled"


class RestaurantStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class LocationType(StrEnum):
    RESTAURANT = "restaurant"
    PICKUP_HUB = "pickup_hub"
    GHOST_KITCHEN = "ghost_kitchen"


class ActorType(StrEnum):
    SYSTEM = "system"
    STAFF = "staff"
    KITCHEN = "kitchen"
    CUSTOMER = "customer"
    INTEGRATION = "integration"
    ADMIN = "admin"
