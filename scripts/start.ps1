$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'build-local.ps1')
Push-Location (Join-Path $root 'backend')
try {
    Write-Host 'PULSE XI running at http://127.0.0.1:8000' -ForegroundColor Cyan
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
    Pop-Location
}
