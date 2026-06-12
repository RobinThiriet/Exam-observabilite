from shared.config import Config
from shared.rabbitmq_connector import RabbitMQConnector
from shared.redis_connector import RedisConnector
from shared.metrics import (
    DEPENDENCY_FAILURES,
    KITCHEN_ORDERS_PROCESSED,
    RESERVATION_STATUS_TRANSITIONS,
    start_metrics_server_if_needed,
)

import threading
import json
import logging
import os
import time

# Setup logging
Config().setup_logging("kitchen.log")
start_metrics_server_if_needed(int(os.environ.get("METRICS_PORT", "9102")))

# Initialize Tracing
from shared.tracing import init_tracer
init_tracer("kitchen_service")

# Callback function
def callback(ch, method, properties, body):
    try:
        if not body:
            logging.warning("Received empty body in kitchen callback")
            return

        order = json.loads(body)
        logging.info(f"Order received in kitchen: {order}")
        
        # Update reservation status in Redis
        # Redis returns a dict, so we access fields via ['key']
        reservation_id = order.get("reservation_id")
        if not reservation_id:
            logging.error("No reservation_id in order message")
            return

        reservation = RedisConnector().get(reservation_id)
        if reservation:
            reservation["status"] = Config().get_reservation_status("cooking")
            RedisConnector().set(reservation_id, reservation)
            KITCHEN_ORDERS_PROCESSED.inc()
            RESERVATION_STATUS_TRANSITIONS.labels(
                service="kitchen_service",
                status=Config().get_reservation_status("cooking")
            ).inc()
            logging.info(f"Reservation {reservation_id} status updated to COOKING")
        else:
            DEPENDENCY_FAILURES.labels(
                service="kitchen_service",
                dependency="redis"
            ).inc()
            logging.warning(f"Reservation {reservation_id} not found in Redis")
        
        # Notify that order is cooked
        RabbitMQConnector().publish(Config().get_queue("kitchen"), order)
        logging.info(f"Order {reservation_id} sent to kitchen queue (done)")

    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON in kitchen callback: {body}. Error: {e}")
    except Exception as e:
        logging.error(f"Error in kitchen callback: {e}")

# Thread to listen to reservations
def listen_orders():
    RabbitMQConnector().listen(Config().get_queue("orders"), callback)

if __name__ == "__main__":
    logging.info("Kitchen service starting...")
    thread = threading.Thread(target=listen_orders)
    thread.daemon = True
    thread.start()
    
    # Keep the main thread alive
    while True:
        time.sleep(1)
