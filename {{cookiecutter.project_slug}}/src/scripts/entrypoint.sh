#!/bin/sh
set -eu

# `makemigrations` is deliberately NOT run here: migrations are source code and
# must be reviewed and committed, never invented at container start.
if [ "${RUN_MIGRATIONS:-True}" = "True" ]; then
  echo "Running migrations..."
  python manage.py migrate --noinput
else
  echo "Skipping migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS})."
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Anything passed as a command overrides the server (used by the worker
# services, which share this image).
if [ "$#" -gt 0 ]; then
  echo "Starting: $*"
  exec "$@"
fi

echo "Starting server..."
exec python -m uvicorn config.server.asgi:application \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "${WEB_CONCURRENCY:-4}" \
  --lifespan off
