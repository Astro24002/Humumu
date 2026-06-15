#!/bin/sh
set -e

echo "entrypoint: running database migrations..."
/app/server migrate

echo "entrypoint: migrations complete, starting server..."
exec /app/server
