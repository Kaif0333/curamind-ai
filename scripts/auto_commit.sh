#!/usr/bin/env bash
set -euo pipefail

AUTHOR_NAME="${GIT_AUTHOR_NAME:-Kaif0333}"
AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-222562291+Kaif0333@users.noreply.github.com}"

git add .
git -c user.name="${AUTHOR_NAME}" -c user.email="${AUTHOR_EMAIL}" \
    commit -m "Auto update: $(date)"
git push origin main
