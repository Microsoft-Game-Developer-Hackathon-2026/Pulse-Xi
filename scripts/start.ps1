param([ValidateRange(1024, 65535)][int]$Port = 8000)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'build-local.ps1')
Push-Location (Join-Path $root 'backend')
try {
    Write-Host "PULSE XI running at http://127.0.0.1:$Port" -ForegroundColor Cyan
    python -m uvicorn app.main:app --loop app.local_event_loop:create_loop --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'PULSE XI server failed to start or exited with an error' }
} finally {
    Pop-Location
}
