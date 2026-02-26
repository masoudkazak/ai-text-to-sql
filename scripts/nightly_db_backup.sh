#!/usr/bin/env bash
set -euo pipefail

# Nightly PostgreSQL backup script.
# Expected env vars: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${SCRIPT_DIR}/../backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

mkdir -p "${BACKUP_DIR}"

if [[ -z "${POSTGRES_DB:-}" ]]; then
  echo "POSTGRES_DB is required" >&2
  exit 1
fi

if [[ -z "${POSTGRES_USER:-}" ]]; then
  echo "POSTGRES_USER is required" >&2
  exit 1
fi

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
  echo "POSTGRES_PASSWORD is required" >&2
  exit 1
fi

export PGPASSWORD="${POSTGRES_PASSWORD}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TIMESTAMP}.dump"

pg_dump \
  --host "${POSTGRES_HOST}" \
  --port "${POSTGRES_PORT}" \
  --username "${POSTGRES_USER}" \
  --format custom \
  --file "${TARGET_FILE}" \
  "${POSTGRES_DB}"

find "${BACKUP_DIR}" -type f -name "*.dump" -mtime +"${RETENTION_DAYS}" -delete
echo "Backup created: ${TARGET_FILE}"
