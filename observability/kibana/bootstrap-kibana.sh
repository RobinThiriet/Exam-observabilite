#!/bin/sh
set -eu

KIBANA_URL="${KIBANA_URL:-http://kibana:5601}"

echo "Waiting for Kibana API..."
until curl -s "$KIBANA_URL/api/status" | grep -q '"level":"available"'; do
  sleep 5
done

curl -s -X POST "$KIBANA_URL/api/saved_objects/_import?overwrite=true" \
  -H 'kbn-xsrf: true' \
  --form file=@/scripts/restaurant-logs-dashboard.ndjson >/dev/null

echo "Kibana bootstrap complete."
