#!/bin/sh
set -eu

CERT_DIR="/etc/nginx/certs"
FULLCHAIN="${CERT_DIR}/fullchain.pem"
PRIVKEY="${CERT_DIR}/privkey.pem"

mkdir -p "${CERT_DIR}"

if [ ! -f "${FULLCHAIN}" ] || [ ! -f "${PRIVKEY}" ]; then
    openssl req \
        -x509 \
        -nodes \
        -days 365 \
        -newkey rsa:2048 \
        -keyout "${PRIVKEY}" \
        -out "${FULLCHAIN}" \
        -subj "/CN=localhost"
fi

exec nginx -g "daemon off;"
