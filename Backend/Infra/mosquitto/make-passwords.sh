#!/usr/bin/env bash
# Creates Backend/Infra/mosquitto/passwd (gitignored) using mosquitto_passwd inside the
# mosquitto container. Users: the backend and simulator (from .env) and test devices BIN-001, BIN-002.
# Run from the repo root: bash Backend/Infra/mosquitto/make-passwords.sh
set -euo pipefail

# Stop Git Bash on Windows from rewriting /mosquitto/... paths
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")/../../.."

if [ ! -f .env ]; then
  echo "No .env found. Run: cp .env.example .env" >&2
  exit 1
fi

# Read a value from .env (tr removes Windows CRLF endings)
get_env() {
  grep "^$1=" .env | head -n 1 | cut -d= -f2- | tr -d '\r'
}

BACKEND_USER=$(get_env MQTT_USER)
BACKEND_PASSWORD=$(get_env MQTT_PASSWORD)
DEVICE_PASSWORD=$(get_env MQTT_TEST_DEVICE_PASSWORD)
SIM_USER=$(get_env MQTT_SIM_USER)
SIM_PASSWORD=$(get_env MQTT_SIM_PASSWORD)

docker compose run --rm --no-deps --entrypoint sh mqtt -c '
  set -e
  f=/mosquitto/config/passwd
  rm -f "$f"
  touch "$f"
  mosquitto_passwd -b "$f" "$1" "$2"
  mosquitto_passwd -b "$f" "$4" "$5"
  mosquitto_passwd -b "$f" BIN-001 "$3"
  mosquitto_passwd -b "$f" BIN-002 "$3"
' sh "$BACKEND_USER" "$BACKEND_PASSWORD" "$DEVICE_PASSWORD" "$SIM_USER" "$SIM_PASSWORD"

echo "Created Backend/Infra/mosquitto/passwd with users: $BACKEND_USER, $SIM_USER, BIN-001, BIN-002"
echo "If the broker is already running: docker compose restart mqtt"
