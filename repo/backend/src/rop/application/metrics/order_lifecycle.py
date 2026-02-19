from __future__ import annotations

from datetime import datetime, timezone

from prometheus_client import Counter, Gauge, Histogram

from rop.domain.order.entities import Order, OrderStatus

ORDERS_TOTAL = Counter(
    "rop_orders_total",
    "Total number of orders observed by status.",
    ["restaurant_id", "status"],
)

ORDER_TRANSITION_TOTAL = Counter(
    "rop_order_transition_total",
    "Total number of order lifecycle transitions.",
    ["from", "to"],
)

ORDER_TIME_TO_ACCEPT_SECONDS = Histogram(
    "rop_order_time_to_accept_seconds",
    "Time between order placement and acceptance.",
)

ORDER_TIME_TO_READY_SECONDS = Histogram(
    "rop_order_time_to_ready_seconds",
    "Time between order placement and readiness.",
)

KITCHEN_QUEUE_SIZE = Gauge(
    "rop_kitchen_queue_size",
    "Current number of orders returned by queue queries.",
    ["restaurant_id", "status"],
)

TABLES_CLOSED_TOTAL = Counter(
    "rop_tables_closed_total",
    "Total number of tables closed.",
    ["restaurant_id"],
)

TABLES_OPENED_TOTAL = Counter(
    "rop_tables_opened_total",
    "Total number of tables opened.",
    ["restaurant_id"],
)

TABLE_CLOSE_BLOCKED_TOTAL = Counter(
    "rop_table_close_blocked_total",
    "Total number of blocked table close attempts.",
    ["restaurant_id", "reason"],
)

TABLES_LIST_REQUESTS_TOTAL = Counter(
    "rop_tables_list_requests_total",
    "Total number of table registry list requests.",
    ["restaurant_id", "status"],
)


def record_order_status(order: Order) -> None:
    ORDERS_TOTAL.labels(
        restaurant_id=str(order.restaurant_id),
        status=order.status.value,
    ).inc()


def record_transition(from_status: OrderStatus, to_status: OrderStatus) -> None:
    ORDER_TRANSITION_TOTAL.labels(**{"from": from_status.value, "to": to_status.value}).inc()


def record_time_to_accept(order: Order, now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    ORDER_TIME_TO_ACCEPT_SECONDS.observe(max((current - order.created_at).total_seconds(), 0.0))


def record_time_to_ready(order: Order, now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    ORDER_TIME_TO_READY_SECONDS.observe(max((current - order.created_at).total_seconds(), 0.0))


def record_kitchen_queue_size(restaurant_id: str, status: str, size: int) -> None:
    KITCHEN_QUEUE_SIZE.labels(restaurant_id=restaurant_id, status=status).set(size)


def record_table_closed(restaurant_id: str) -> None:
    TABLES_CLOSED_TOTAL.labels(restaurant_id=restaurant_id).inc()


def record_table_opened(restaurant_id: str) -> None:
    TABLES_OPENED_TOTAL.labels(restaurant_id=restaurant_id).inc()


def record_table_close_blocked(restaurant_id: str, reason: str) -> None:
    TABLE_CLOSE_BLOCKED_TOTAL.labels(restaurant_id=restaurant_id, reason=reason).inc()


def record_tables_list_request(restaurant_id: str, status: str) -> None:
    TABLES_LIST_REQUESTS_TOTAL.labels(restaurant_id=restaurant_id, status=status).inc()
