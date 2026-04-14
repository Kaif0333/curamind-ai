#!/usr/bin/env bash
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-./backups}"

if [[ "$#" -gt 0 ]]; then
  archives=("$@")
else
  mapfile -t archives < <(
    find "${BACKUP_ROOT}" -type f \( -name "*.sql.gz" -o -name "*.archive.gz" \) | sort
  )
fi

if [[ "${#archives[@]}" -eq 0 ]]; then
  echo "No backup archives found to verify."
  exit 1
fi

for archive in "${archives[@]}"; do
  if [[ ! -f "${archive}" ]]; then
    echo "Backup archive not found: ${archive}" >&2
    exit 1
  fi
  gzip -t "${archive}"
  size_bytes="$(wc -c < "${archive}")"
  echo "Verified ${archive} (${size_bytes} bytes)"
done

echo "All backup archives passed gzip integrity checks."
