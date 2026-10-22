param([Parameter(Mandatory = $true)][string]$Url)
$ErrorActionPreference = "Stop"
if ($Url -notmatch '^https://[^/?#]+/?$') { throw "Pass only the deployed HTTPS origin, for example https://app.region.azurecontainerapps.io" }
python scripts/container-smoke.py --url $Url
if ($LASTEXITCODE -ne 0) { throw "HTTP/API/WebSocket deployed smoke failed." }

$frontend = Join-Path $PSScriptRoot "../../frontend"
$frontend = [System.IO.Path]::GetFullPath($frontend)
Push-Location $frontend
try {
    $env:PULSE_DEMO_URL = $Url.TrimEnd('/')
    npx.cmd playwright test --config=playwright.deployed.config.ts
    if ($LASTEXITCODE -ne 0) { throw "Deployed browser journey failed." }
}
finally {
    Remove-Item Env:PULSE_DEMO_URL -ErrorAction SilentlyContinue
    Pop-Location
}
