import logging
from prometheus_client import Counter, Gauge, Histogram, start_http_server

_metrics_server_started = False

RESERVATIONS_CREATED = Counter(
    "restaurant_reservations_created_total",
    "Total number of reservations created.",
)

RESERVATION_STATUS_TRANSITIONS = Counter(
    "restaurant_reservation_status_transitions_total",
    "Total number of reservation status transitions.",
    ["service", "status"],
)

ORDERS_SUBMITTED = Counter(
    "restaurant_orders_submitted_total",
    "Total number of orders submitted.",
)

KITCHEN_ORDERS_PROCESSED = Counter(
    "restaurant_kitchen_orders_processed_total",
    "Total number of orders processed by the kitchen.",
)

PAYMENTS_PROCESSED = Counter(
    "restaurant_payments_processed_total",
    "Total number of payments processed.",
    ["outcome"],
)

PAYMENT_PROCESSING_SECONDS = Histogram(
    "restaurant_payment_processing_seconds",
    "Payment processing latency in seconds.",
    buckets=(0.1, 0.3, 0.5, 1, 2, 3, 5, 10),
)

DEPENDENCY_FAILURES = Counter(
    "restaurant_dependency_failures_total",
    "Total number of dependency failures observed by the application.",
    ["service", "dependency"],
)

ACTIVE_RESERVATIONS = Gauge(
    "restaurant_active_reservations",
    "Current number of active reservations stored in Redis.",
)


def start_metrics_server_if_needed(port):
    global _metrics_server_started
    if _metrics_server_started:
        return

    start_http_server(port, addr="0.0.0.0")
    _metrics_server_started = True
    logging.info("Prometheus metrics server listening on port %s", port)
