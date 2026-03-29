#!/usr/bin/env bash
set -euo pipefail

INPUT_PATH="${1:-}"
MONGO_DB_NAME="${MONGO_DB_NAME:-curamind}"

if [[ -z "${INPUT_PATH}" || ! -f "${INPUT_PATH}" ]]; then
  echo "Usage: ./scripts/restore_mongodb.sh <backup.archive.gz>"
  exit 1
fi

cat "${INPUT_PATH}" | docker compose exec -T mongodb sh -lc \
  "mongorestore --archive --gzip --drop --nsInclude '${MONGO_DB_NAME}.*'"

echo "MongoDB restore completed from ${INPUT_PATH}"
