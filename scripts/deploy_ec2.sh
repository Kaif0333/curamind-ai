#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"
BASE_URL="${BASE_URL:-http://127.0.0.1}"

./scripts/validate_production_env.sh "${ENV_FILE}"

echo "Building and starting CuraMind AI..."
docker compose --env-file "${ENV_FILE}" up -d --build

echo "Running post-deployment health checks against ${BASE_URL}..."
./scripts/post_deploy_healthcheck.sh "${BASE_URL}"

echo "Deployment completed successfully."
