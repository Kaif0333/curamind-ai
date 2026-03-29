#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1}"

echo "Checking CuraMind AI deployment at ${BASE_URL}"

check() {
  local path="$1"
  local expected="${2:-200}"
  local status
  status="$(curl -k -s -o /dev/null -w "%{http_code}" "${BASE_URL}${path}")"
  if [[ "${status}" != "${expected}" ]]; then
    echo "FAILED ${path} -> ${status} (expected ${expected})"
    exit 1
  fi
  echo "OK ${path} -> ${status}"
}

check "/healthz"
check "/readyz"
check "/utils/health"
check "/ai/health"
check "/ai/ready"
check "/ai/model-info"

echo "All deployment health checks passed."
