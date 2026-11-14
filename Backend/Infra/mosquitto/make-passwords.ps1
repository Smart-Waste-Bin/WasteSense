# PowerShell version of make-passwords.sh.
# Run from the repo root: .\Backend\Infra\mosquitto\make-passwords.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\..\..")

if (-not (Test-Path .env)) {
    Write-Error "No .env found. Run: Copy-Item .env.example .env"
}

function Get-EnvValue($name) {
    $line = Get-Content .env | Where-Object { $_ -match "^$name=" } | Select-Object -First 1
    return ($line -replace "^$name=", "").Trim()
}

$backendUser = Get-EnvValue "MQTT_USER"
$backendPassword = Get-EnvValue "MQTT_PASSWORD"
$devicePassword = Get-EnvValue "MQTT_TEST_DEVICE_PASSWORD"

$script = 'set -e; f=/mosquitto/config/passwd; rm -f "$f"; touch "$f"; mosquitto_passwd -b "$f" "$1" "$2"; mosquitto_passwd -b "$f" bin-001 "$3"; mosquitto_passwd -b "$f" bin-002 "$3"'

docker compose run --rm --no-deps --entrypoint sh mqtt -c $script sh $backendUser $backendPassword $devicePassword
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Created Backend/Infra/mosquitto/passwd with users: $backendUser, bin-001, bin-002"
Write-Host "If the broker is already running: docker compose restart mqtt"
