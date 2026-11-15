#!/bin/sh
# Runs inside the "mqtt-setup" container before the broker starts (see docker-compose.yml).
# 1. Makes the dev TLS certs, only if they are missing.
# 2. Rebuilds the passwd file from .env every time, so a changed password just needs
#    "docker compose up" again.
# DEVELOPMENT ONLY. Never use these certs on a real deployment.
set -eu

cd /mosquitto/config

if [ ! -f certs/server.crt ] || [ ! -f certs/server.key ] || [ ! -f certs/ca.crt ]; then
  echo "No dev certs found, making them..."
  apk add --no-cache openssl > /dev/null
  mkdir -p certs
  cd certs

  # Certificate authority (CA)
  openssl req -x509 -new -nodes -newkey rsa:2048 -days 825 \
    -keyout ca.key -out ca.crt -subj "/CN=SmartBin Dev CA"

  # Server cert signed by the CA. Valid for localhost and the compose name "mqtt".
  openssl req -new -nodes -newkey rsa:2048 \
    -keyout server.key -out server.csr -subj "/CN=localhost"
  printf "subjectAltName=DNS:localhost,DNS:mqtt,IP:127.0.0.1\n" > server.ext
  openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days 825 -extfile server.ext
  rm -f server.csr server.ext ca.srl

  # The broker runs as its own user, so it must be able to read the key.
  chmod 644 server.key
  cd ..
fi

# Older .env files have no simulator user yet: fall back to the .env.example values.
MQTT_SIM_USER="${MQTT_SIM_USER:-smartbin-simulator}"
MQTT_SIM_PASSWORD="${MQTT_SIM_PASSWORD:-change-me-sim}"

echo "Making passwd for: $MQTT_USER, $MQTT_SIM_USER, BIN-001, BIN-002"
rm -f passwd
touch passwd
mosquitto_passwd -b passwd "$MQTT_USER" "$MQTT_PASSWORD"
mosquitto_passwd -b passwd "$MQTT_SIM_USER" "$MQTT_SIM_PASSWORD"
mosquitto_passwd -b passwd BIN-001 "$MQTT_TEST_DEVICE_PASSWORD"
mosquitto_passwd -b passwd BIN-002 "$MQTT_TEST_DEVICE_PASSWORD"
chmod 644 passwd

echo "MQTT setup done."
