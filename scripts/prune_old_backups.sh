#!/usr/bin/env bash
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-./backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

if ! [[ "${BACKUP_RETENTION_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "BACKUP_RETENTION_DAYS must be an integer number of days." >&2
  exit 1
fi

if [[ ! -d "${BACKUP_ROOT}" ]]; then
  echo "Backup directory ${BACKUP_ROOT} does not exist. Nothing to prune."
  exit 0
fi

echo "Pruning CuraMind AI backups older than ${BACKUP_RETENTION_DAYS} days from ${BACKUP_ROOT}..."
find "${BACKUP_ROOT}" \
  -type f \
  \( -name "*.sql.gz" -o -name "*.archive.gz" \) \
  -mtime +"${BACKUP_RETENTION_DAYS}" \
  -print \
  -delete

echo "Backup pruning complete."
