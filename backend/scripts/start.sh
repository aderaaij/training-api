#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting Training API..."
if [ "$ENVIRONMENT" = "LOCAL" ]; then
    fastapi dev app/main.py --host 0.0.0.0 --port 8001
else
    fastapi run app/main.py --host 0.0.0.0 --port 8001
fi
