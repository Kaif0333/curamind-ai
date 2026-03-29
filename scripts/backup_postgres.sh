#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
POSTGRES_DB="${POSTGRES_DB:-curamind}"
POSTGRES_USER="${POSTGRES_USER:-curamind}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-curamind}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT_PATH="${1:-${BACKUP_DIR}/postgres-${POSTGRES_DB}-${TIMESTAMP}.sql.gz}"

mkdir -p "${BACKUP_DIR}"

docker compose exec -T postgres env PGPASSWORD="${POSTGRES_PASSWORD}" \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" | gzip -c > "${OUTPUT_PATH}"

echo "PostgreSQL backup written to ${OUTPUT_PATH}"
