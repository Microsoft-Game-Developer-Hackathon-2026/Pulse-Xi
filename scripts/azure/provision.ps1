param(
    [Parameter(Mandatory = $true)][string]$ResourceGroup,
    [Parameter(Mandatory = $true)][string]$Image,
    [string]$Location = "eastus",
    [string]$EnvironmentName = "pulse-xi-demo-env",
    [string]$AppName = "pulse-xi-demo",
    [switch]$ConfirmProvisioning
)
$ErrorActionPreference = "Stop"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) { throw "Azure CLI is required. No resources were created." }
if ($Image -notmatch '^ghcr\.io/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+$') {
    throw "Image must be an immutable, public ghcr.io image reference; credentials are not accepted."
}
$template = Join-Path $PSScriptRoot "../../infra/azure/main.bicep"
$template = [System.IO.Path]::GetFullPath($template)
if (-not (az group exists --name $ResourceGroup | ConvertFrom-Json)) {
    throw "Resource group '$ResourceGroup' does not exist. Provisioning never creates resource groups."
}
Write-Host "Target: existing resource group '$ResourceGroup', location '$Location', Container App '$AppName', environment '$EnvironmentName'."
Write-Host "An Azure Container Apps environment and public Container App will be created or updated. This can incur charges."
az deployment group what-if --resource-group $ResourceGroup --template-file $template `
    --parameters location=$Location environmentName=$EnvironmentName appName=$AppName image=$Image
if ($LASTEXITCODE -ne 0) { throw "Azure what-if failed; no deployment was attempted." }
if (-not $ConfirmProvisioning) { Write-Host "Dry run only. Re-run with -ConfirmProvisioning after reviewing cost and target."; exit 0 }
$confirmation = Read-Host "Type CREATE PULSE XI AZURE RESOURCES to continue"
if ($confirmation -cne "CREATE PULSE XI AZURE RESOURCES") { throw "Confirmation did not match; no resources were created." }
az deployment group create --name "pulse-xi-demo-$(Get-Date -Format yyyyMMddHHmmss)" `
    --resource-group $ResourceGroup --template-file $template `
    --parameters location=$Location environmentName=$EnvironmentName appName=$AppName image=$Image
if ($LASTEXITCODE -ne 0) { throw "Deployment failed. Inspect the named deployment and Azure activity log before retrying." }
