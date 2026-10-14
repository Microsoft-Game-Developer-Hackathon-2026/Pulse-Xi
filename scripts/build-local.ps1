$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    npm --prefix $frontend ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
}
python -m pip install -r (Join-Path $root 'backend/requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
Push-Location $frontend
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
} finally {
    Pop-Location
}
