#!/bin/sh
set -eu

# -f makes curl exit non-zero on 4xx/5xx. Without it this check passes on a 404
# and the container is reported healthy while the API is broken.
URL="http://localhost:${HEALTHCHECK_PORT:-8000}${HEALTHCHECK_PATH:-/api/v1/health/}"

if curl -fsS --max-time 5 "$URL" > /dev/null; then
  exit 0
else
  echo "Django healthcheck failed: $URL"
  exit 1
fi
