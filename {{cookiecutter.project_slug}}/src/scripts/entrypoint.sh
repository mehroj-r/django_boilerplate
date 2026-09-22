#!/bin/sh
set -eu

# No makemigrations: migrations are source code, not something to invent here.
if [ "${RUN_MIGRATIONS:-True}" = "True" ]; then
  echo "Running migrations..."
  python manage.py migrate --noinput
else
  echo "Skipping migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS})."
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput

# A passed command overrides the server; the worker services rely on this.
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
