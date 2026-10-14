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
    npm exec -- tsc -b
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript typecheck failed' }
    New-Item -ItemType Directory -Force 'dist/assets' | Out-Null
    $bundler = Join-Path $frontend 'node_modules/@esbuild/win32-x64/esbuild.exe'
    if (-not (Test-Path $bundler)) { throw 'Windows esbuild binary missing; run npm ci in frontend' }
    & $bundler 'src/main.tsx' '--bundle' '--outdir=dist/assets' '--jsx=automatic' '--format=esm' '--platform=browser' '--loader:.css=css' '--minify'
    if ($LASTEXITCODE -ne 0) { throw 'Frontend bundle failed' }
    $html = (Get-Content -Raw 'index.html').Replace('<script type="module" src="/src/main.tsx"></script>', '<link rel="stylesheet" href="/assets/main.css"/><script type="module" src="/assets/main.js"></script>')
    Set-Content -Path 'dist/index.html' -Value $html -Encoding utf8
} finally {
    Pop-Location
}
