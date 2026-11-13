# DEVELOPMENT ONLY. PowerShell version of make-dev-certs.sh.
# Makes a self-signed CA and a server cert for the local broker.
# Needs openssl: it comes with Git for Windows (C:\Program Files\Git\usr\bin\openssl.exe).
# Run from the repo root: .\Infra\mosquitto\make-dev-certs.ps1
$ErrorActionPreference = "Stop"

$openssl = (Get-Command openssl -ErrorAction SilentlyContinue).Source
if (-not $openssl) { $openssl = "$env:ProgramFiles\Git\usr\bin\openssl.exe" }
if (-not (Test-Path $openssl)) { Write-Error "openssl not found. Install Git for Windows or run make-dev-certs.sh in Git Bash." }

$certs = Join-Path $PSScriptRoot "certs"
New-Item -ItemType Directory -Force $certs | Out-Null
Set-Location $certs

function Run([string[]]$opensslArgs) {
    & $openssl @opensslArgs
    if ($LASTEXITCODE -ne 0) { throw "openssl failed: $opensslArgs" }
}

# 1. Certificate authority (CA)
Run @("req", "-x509", "-new", "-nodes", "-newkey", "rsa:2048", "-days", "825", "-keyout", "ca.key", "-out", "ca.crt", "-subj", "/CN=SmartBin Dev CA")

# 2. Server key and signing request
Run @("req", "-new", "-nodes", "-newkey", "rsa:2048", "-keyout", "server.key", "-out", "server.csr", "-subj", "/CN=localhost")

# 3. Sign the server cert with the CA. Valid for localhost and the compose name "mqtt".
Set-Content -Path server.ext -Value "subjectAltName=DNS:localhost,DNS:mqtt,IP:127.0.0.1" -Encoding ascii
Run @("x509", "-req", "-in", "server.csr", "-CA", "ca.crt", "-CAkey", "ca.key", "-CAcreateserial", "-out", "server.crt", "-days", "825", "-extfile", "server.ext")

Remove-Item server.csr, server.ext, ca.srl -ErrorAction SilentlyContinue

Write-Host "DEV ONLY certs created in Infra/mosquitto/certs/ (ca.crt, server.crt, server.key)"
