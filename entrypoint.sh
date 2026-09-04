#!/bin/sh
set -e

# Production enables the fetch/notify scheduler by default (Task 12 gate).
export HUMUMU_ENABLE_SCHEDULER="${HUMUMU_ENABLE_SCHEDULER:-1}"

echo "entrypoint: running database migrations..."
python -m scripts.migrate

# Optional built-in journals + CAS facets (+ demo journal attach). Off by
# default so restarts do not surprise overwrite admin edits unless enabled.
if [ "${HUMUMU_SEED_JOURNALS:-0}" = "1" ]; then
  echo "entrypoint: seeding journals from data/journals_seed.json..."
  python -m scripts.seed_journals
  echo "entrypoint: seeding CAS categories (+ attach) from data/cas_*_seed.json..."
  python -m scripts.seed_cas_categories --attach
fi

echo "entrypoint: migrations complete, starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${SERVER_PORT:-8080}"
