#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups/mongodb}"
MONGO_DB_NAME="${MONGO_DB_NAME:-curamind}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT_PATH="${1:-${BACKUP_DIR}/mongodb-${MONGO_DB_NAME}-${TIMESTAMP}.archive.gz}"

mkdir -p "${BACKUP_DIR}"

docker compose exec -T mongodb sh -lc \
  "mongodump --archive --gzip --db '${MONGO_DB_NAME}'" > "${OUTPUT_PATH}"

echo "MongoDB backup written to ${OUTPUT_PATH}"
