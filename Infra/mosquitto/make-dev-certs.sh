#!/usr/bin/env bash
# DEVELOPMENT ONLY. Makes a self-signed CA and a server cert for the local broker.
# Never use these certs on a real deployment.
# Output: Infra/mosquitto/certs/ (gitignored)
# Run from the repo root: bash Infra/mosquitto/make-dev-certs.sh
set -euo pipefail

# Stop Git Bash on Windows from rewriting "/CN=..." into a file path
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")"
mkdir -p certs
cd certs

# 1. Certificate authority (CA)
openssl req -x509 -new -nodes -newkey rsa:2048 -days 825 \
  -keyout ca.key -out ca.crt -subj "/CN=SmartBin Dev CA"

# 2. Server key and signing request
openssl req -new -nodes -newkey rsa:2048 \
  -keyout server.key -out server.csr -subj "/CN=localhost"

# 3. Sign the server cert with the CA. Valid for localhost and the compose name "mqtt".
printf "subjectAltName=DNS:localhost,DNS:mqtt,IP:127.0.0.1\n" > server.ext
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -extfile server.ext

rm -f server.csr server.ext ca.srl

# Mosquitto runs as its own user inside the container, so on Linux/macOS it
# cannot read a key that only you can read. Fine for a dev-only key.
chmod 644 server.key

echo "DEV ONLY certs created in Infra/mosquitto/certs/ (ca.crt, server.crt, server.key)"
