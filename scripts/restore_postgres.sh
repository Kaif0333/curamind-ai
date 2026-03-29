#!/usr/bin/env bash
set -euo pipefail

INPUT_PATH="${1:-}"
POSTGRES_DB="${POSTGRES_DB:-curamind}"
POSTGRES_USER="${POSTGRES_USER:-curamind}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-curamind}"

if [[ -z "${INPUT_PATH}" || ! -f "${INPUT_PATH}" ]]; then
  echo "Usage: ./scripts/restore_postgres.sh <backup.sql.gz>"
  exit 1
fi

gunzip -c "${INPUT_PATH}" | docker compose exec -T postgres env PGPASSWORD="${POSTGRES_PASSWORD}" \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

echo "PostgreSQL restore completed from ${INPUT_PATH}"
