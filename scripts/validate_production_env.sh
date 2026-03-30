#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment file not found: ${ENV_FILE}"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

required_vars=(
  DJANGO_ENV
  DJANGO_SECRET_KEY
  ALLOWED_HOSTS
  CSRF_TRUSTED_ORIGINS
  CLOUDWATCH_LOG_GROUP_PREFIX
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  AWS_REGION
  AWS_S3_PRIVATE_BUCKET
)

failed=0
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required production variable: ${var_name}"
    failed=1
  fi
done

if [[ "${DJANGO_ENV:-}" != "production" ]]; then
  echo "DJANGO_ENV must be set to production."
  failed=1
fi

if [[ "${DEBUG:-False}" =~ ^([Tt]rue|1|yes)$ ]]; then
  echo "DEBUG must be disabled in production."
  failed=1
fi

if [[ "${DJANGO_SECRET_KEY:-}" == "curamind-local-development-secret-key-please-change" ]]; then
  echo "DJANGO_SECRET_KEY is still using the local development default."
  failed=1
fi

if [[ "${ALLOWED_HOSTS:-}" == "*" ]]; then
  echo "ALLOWED_HOSTS must not be '*' in production."
  failed=1
fi

for secure_var in SECURE_SSL_REDIRECT SESSION_COOKIE_SECURE CSRF_COOKIE_SECURE; do
  if [[ "${!secure_var:-True}" != "True" ]]; then
    echo "${secure_var} should be True in production."
    failed=1
  fi
done

if [[ "${failed}" -ne 0 ]]; then
  echo "Production environment validation failed."
  exit 1
fi

echo "Production environment validation passed."
