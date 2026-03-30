#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root on the EC2 host."
  exit 1
fi

CONFIG_SOURCE="${1:-./infrastructure/aws/cloudwatch-agent-config.json}"
LOG_GROUP_PREFIX="${CLOUDWATCH_LOG_GROUP_PREFIX:-/curamind/production}"
TMP_CONFIG="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.generated.json"

if [[ ! -f "${CONFIG_SOURCE}" ]]; then
  echo "CloudWatch agent config not found: ${CONFIG_SOURCE}"
  exit 1
fi

case "$(uname -m)" in
  x86_64)
    PACKAGE_URL="https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb"
    ;;
  aarch64|arm64)
    PACKAGE_URL="https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/arm64/latest/amazon-cloudwatch-agent.deb"
    ;;
  *)
    echo "Unsupported architecture: $(uname -m)"
    exit 1
    ;;
esac

apt-get update
apt-get install -y curl
curl -fsSL -o /tmp/amazon-cloudwatch-agent.deb "${PACKAGE_URL}"
dpkg -i /tmp/amazon-cloudwatch-agent.deb

sed "s#__LOG_GROUP_PREFIX__#${LOG_GROUP_PREFIX}#g" "${CONFIG_SOURCE}" > "${TMP_CONFIG}"

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c "file:${TMP_CONFIG}" \
  -s

echo "CloudWatch agent installed and started with log group prefix ${LOG_GROUP_PREFIX}."
