#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${SCRIPT_DIR}/../backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_METHOD="${BACKUP_METHOD:-auto}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres_prod}"
DOCKER_BACKUP_DIR="${DOCKER_BACKUP_DIR:-/backups}"

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
TARGET_BASENAME="$(basename "${TARGET_FILE}")"

dump_local() {
  pg_dump \
    --host "${POSTGRES_HOST}" \
    --port "${POSTGRES_PORT}" \
    --username "${POSTGRES_USER}" \
    --format custom \
    --file "${TARGET_FILE}" \
    "${POSTGRES_DB}"
}

dump_docker() {
  docker exec \
    -e PGPASSWORD="${POSTGRES_PASSWORD}" \
    "${POSTGRES_CONTAINER}" \
    pg_dump \
      --username "${POSTGRES_USER}" \
      --format custom \
      --file "${DOCKER_BACKUP_DIR}/${TARGET_BASENAME}" \
      "${POSTGRES_DB}"
}

cleanup_local() {
  find "${BACKUP_DIR}" -type f -name "*.dump" -mtime +"${RETENTION_DAYS}" -delete
}

cleanup_docker() {
  docker exec "${POSTGRES_CONTAINER}" \
    find "${DOCKER_BACKUP_DIR}" -type f -name "*.dump" -mtime +"${RETENTION_DAYS}" -delete
}

run_backup() {
  case "${BACKUP_METHOD}" in
    local)
      command -v pg_dump >/dev/null 2>&1 || {
        echo "BACKUP_METHOD=local but pg_dump is not installed on host" >&2
        exit 1
      }
      dump_local
      cleanup_local
      ;;
    docker)
      command -v docker >/dev/null 2>&1 || {
        echo "BACKUP_METHOD=docker but docker is not available" >&2
        exit 1
      }
      dump_docker
      cleanup_docker
      ;;
    auto)
      if command -v pg_dump >/dev/null 2>&1; then
        dump_local
        cleanup_local
      elif command -v docker >/dev/null 2>&1; then
        dump_docker
        cleanup_docker
      else
        echo "Neither pg_dump nor docker is available for backup" >&2
        exit 1
      fi
      ;;
    *)
      echo "Invalid BACKUP_METHOD: ${BACKUP_METHOD} (use auto|local|docker)" >&2
      exit 1
      ;;
  esac
}

run_backup

echo "Backup created: ${TARGET_FILE}"
