param(
    [Parameter(Mandatory = $true)][string]$ResourceGroup,
    [string]$AppName = "pulse-xi-demo",
    [string]$EnvironmentName = "pulse-xi-demo-env",
    [switch]$DeleteEnvironment,
    [switch]$ConfirmTarget
)
$ErrorActionPreference = "Stop"
if (-not (Get-Command az -ErrorAction SilentlyContinue)) { throw "Azure CLI is required; no resources were changed." }
if (-not $ConfirmTarget) { throw "Pass -ConfirmTarget only after reviewing the resource IDs and expected charges." }

$app = az containerapp show --resource-group $ResourceGroup --name $AppName --output json | ConvertFrom-Json
$env = az containerapp env show --resource-group $ResourceGroup --name $EnvironmentName --output json | ConvertFrom-Json
$containerEnvironmentId = $app.properties.managedEnvironmentId
if (-not $containerEnvironmentId) { $containerEnvironmentId = $app.properties.environmentId }
if ($app.tags.purpose -ne "public-demo" -or $app.tags.application -ne "pulse-xi" -or
    $containerEnvironmentId -ne $env.id) {
    throw "App tags or environment relationship do not match this demo; no resources were changed."
}
if ($DeleteEnvironment -and ($env.tags.purpose -ne "public-demo" -or $env.tags.application -ne "pulse-xi")) {
    throw "Environment does not carry the expected PULSE XI demo tags; no resources were changed."
}
Write-Host "Target app: $($app.id)"
Write-Host "Target environment: $($env.id)"
Write-Host "The resource group and all unrelated resources will be retained."
$confirmation = Read-Host "Type DELETE APP $AppName to delete only this Container App"
if ($confirmation -cne "DELETE APP $AppName") { throw "Confirmation did not match; nothing was deleted." }
az containerapp delete --resource-group $ResourceGroup --name $AppName --yes
if ($LASTEXITCODE -ne 0) { throw "Container App deletion failed; inspect Azure state before retrying." }

if ($DeleteEnvironment) {
    $environmentId = $env.id.ToLowerInvariant()
    $apps = az containerapp list --resource-group $ResourceGroup --output json | ConvertFrom-Json
    $remaining = @($apps | Where-Object {
        $id = $_.properties.managedEnvironmentId
        if (-not $id) { $id = $_.properties.environmentId }
        $id -and $id.ToLowerInvariant() -eq $environmentId
    })
    if ($remaining.Count -gt 0) { throw "Environment still contains other apps ($($remaining.name -join ', ')); it was retained." }
    $environmentConfirmation = Read-Host "Type DELETE ENVIRONMENT $EnvironmentName to delete this now-empty demo environment"
    if ($environmentConfirmation -cne "DELETE ENVIRONMENT $EnvironmentName") { throw "Confirmation did not match; environment retained." }
    az containerapp env delete --resource-group $ResourceGroup --name $EnvironmentName --yes
    if ($LASTEXITCODE -ne 0) { throw "Environment deletion failed; inspect Azure state before retrying." }
}
