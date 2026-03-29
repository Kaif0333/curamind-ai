#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root on the EC2 host."
  exit 1
fi

TARGET_USER="${TARGET_USER:-ubuntu}"
APP_DIR="${APP_DIR:-/opt/curamind-ai}"

apt-get update
apt-get install -y ca-certificates curl gnupg git

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

. /etc/os-release
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl restart docker
usermod -aG docker "${TARGET_USER}"

mkdir -p "${APP_DIR}"
chown -R "${TARGET_USER}:${TARGET_USER}" "${APP_DIR}"

cat <<EOF
Bootstrap complete.

Next steps:
1. sudo -iu ${TARGET_USER}
2. git clone https://github.com/Kaif0333/curamind-ai.git ${APP_DIR}
3. cd ${APP_DIR}
4. cp .env.example .env
5. Edit .env with production secrets and AWS/S3 settings
6. docker compose up -d --build
7. ./scripts/post_deploy_healthcheck.sh https://your-domain
EOF
