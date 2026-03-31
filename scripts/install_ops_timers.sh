#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/curamind-ai}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
BACKUP_SCHEDULE="${BACKUP_SCHEDULE:-*-*-* 02:00:00}"
HEALTHCHECK_SCHEDULE="${HEALTHCHECK_SCHEDULE:-*:0/15}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
BASE_URL="${BASE_URL:-http://127.0.0.1}"
TEMPLATE_DIR="${TEMPLATE_DIR:-infrastructure/systemd}"

render_unit() {
  local template_name="$1"
  local output_name="$2"
  sed \
    -e "s|__APP_DIR__|${APP_DIR}|g" \
    -e "s|__BASE_URL__|${BASE_URL}|g" \
    -e "s|__BACKUP_RETENTION_DAYS__|${BACKUP_RETENTION_DAYS}|g" \
    -e "s|__BACKUP_SCHEDULE__|${BACKUP_SCHEDULE}|g" \
    -e "s|__HEALTHCHECK_SCHEDULE__|${HEALTHCHECK_SCHEDULE}|g" \
    "${TEMPLATE_DIR}/${template_name}" > "${SYSTEMD_DIR}/${output_name}"
}

if [[ ! -d "${TEMPLATE_DIR}" ]]; then
  echo "Template directory not found: ${TEMPLATE_DIR}" >&2
  exit 1
fi

sudo mkdir -p "${SYSTEMD_DIR}"
render_unit "curamind-backup.service" "curamind-backup.service"
render_unit "curamind-backup.timer" "curamind-backup.timer"
render_unit "curamind-healthcheck.service" "curamind-healthcheck.service"
render_unit "curamind-healthcheck.timer" "curamind-healthcheck.timer"

sudo systemctl daemon-reload
sudo systemctl enable --now curamind-backup.timer curamind-healthcheck.timer

echo "Installed CuraMind AI systemd timers."
echo "Backup schedule: ${BACKUP_SCHEDULE}"
echo "Healthcheck schedule: ${HEALTHCHECK_SCHEDULE}"
