#!/bin/sh
set -e

# Production enables the fetch/notify scheduler by default (Task 12 gate).
export HUMUMU_ENABLE_SCHEDULER="${HUMUMU_ENABLE_SCHEDULER:-1}"

echo "entrypoint: running database migrations..."
python -m scripts.migrate

echo "entrypoint: migrations complete, starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${SERVER_PORT:-8080}"
