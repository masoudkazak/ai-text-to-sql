#!/usr/bin/env sh
set -eu

python -m scripts.wait_for_db
alembic upgrade head
python -m scripts.seed_data
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
