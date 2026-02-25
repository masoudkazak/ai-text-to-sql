#!/usr/bin/env sh
set -eu

APP_ENV="${APP_ENV:-production}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
RUN_SEED_DATA="${RUN_SEED_DATA:-0}"

if [ "$RUN_MIGRATIONS" = "1" ]; then
  python -m scripts.wait_for_db
  alembic upgrade head
fi

if [ "$RUN_SEED_DATA" = "1" ]; then
  python -m scripts.seed_data
fi

if [ "$APP_ENV" = "development" ]; then
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-2}"
