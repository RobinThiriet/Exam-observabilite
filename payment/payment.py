import flask
import logging
import os
from shared.redis_connector import RedisConnector
from shared.database_connector import DatabaseConnector
from shared.config import Config
from shared.metrics import (
    ACTIVE_RESERVATIONS,
    DEPENDENCY_FAILURES,
    PAYMENT_PROCESSING_SECONDS,
    PAYMENTS_PROCESSED,
)

# Setup logging
Config().setup_logging("payment.log")

# Initialize Tracing
from shared.tracing import init_tracer, instrument_flask
init_tracer("payment_service")

app = flask.Flask(__name__)
instrument_flask(app)

# Prometheus metrics endpoint (/metrics)
from prometheus_flask_exporter import PrometheusMetrics
PrometheusMetrics(app)

@app.route("/pay", methods=["POST"])
def pay():
    with PAYMENT_PROCESSING_SECONDS.time():
        data = flask.request.json
        if not data:
            return flask.jsonify({"error": "No payment data provided"}), 400
        
        reservation_id = data.get("reservation_id")
        if not reservation_id:
            return flask.jsonify({"error": "Missing reservation_id"}), 400
        
        logging.info(f"Processing payment for reservation {reservation_id}")
        
        # This incident can be re-enabled for the observability exercise.
        import random
        import time
        chaos_enabled = os.environ.get("PAYMENT_CHAOS_ENABLED", "false").lower() == "true"
        if chaos_enabled and random.random() < 0.25:
            time.sleep(2.5)
            error_msg = "CRITICAL: Payment Gateway Timeout. Connection refused by the external bank API."
            PAYMENTS_PROCESSED.labels(outcome="failure").inc()
            DEPENDENCY_FAILURES.labels(
                service="payment_service",
                dependency="external_bank_api"
            ).inc()
            logging.error(error_msg)
            return flask.jsonify({"error": error_msg}), 503
        
        menus = data.get("menus", [])
        total_price = sum(item.get("price", 0) for item in menus)
        
        try:
            DatabaseConnector().save_order(reservation_id, total_price)
        except Exception as e:
            DEPENDENCY_FAILURES.labels(
                service="payment_service",
                dependency="postgresql"
            ).inc()
            logging.error(f"Error saving order for {reservation_id}: {e}")
        
        RedisConnector().delete(reservation_id)
        ACTIVE_RESERVATIONS.set(len(RedisConnector().get_all() or []))
        PAYMENTS_PROCESSED.labels(outcome="success").inc()
        
        logging.info(f"Payment successful for {reservation_id}: {total_price}€")
        return flask.jsonify({
            "message": "Payment successful",
            "reservation_id": reservation_id,
            "total_price": total_price
        }), 200

if __name__ == "__main__":
    # Ensure tables exist
    DatabaseConnector().init_db()
    
    app.run(debug=False, host="0.0.0.0", port=5003)
