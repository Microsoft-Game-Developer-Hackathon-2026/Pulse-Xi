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

function Get-ValidatedResourceIdentity {
    param([object]$ResourceId, [string]$ResourceType)
    # Match the entire ARM path, not a suffix. Names are compared as complete
    # segments, so operator input is never interpolated into the regex.
    $pattern = '\A/subscriptions/(?<subscription>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/resourceGroups/(?<group>[^/]+)/providers/Microsoft\.App/(?<type>[^/]+)/(?<name>[^/]+)\z'
    $identity = $null
    if ($ResourceId -is [string]) {
        $identity = [regex]::Match($ResourceId, $pattern,
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
    }
    if (-not $identity -or -not $identity.Success -or
        -not [string]::Equals($identity.Groups['type'].Value, $ResourceType, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Resource ID is not a complete Microsoft.App/$ResourceType ARM identity; deletion cannot continue."
    }
    return $identity
}

function Get-ValidatedResourceSubscription {
    param([object]$ResourceId, [string]$ResourceType, [string]$ResourceName, [string]$GroupName)
    $identity = Get-ValidatedResourceIdentity -ResourceId $ResourceId -ResourceType $ResourceType
    $comparison = [System.StringComparison]::OrdinalIgnoreCase
    if (-not [string]::Equals($identity.Groups['group'].Value, $GroupName, $comparison) -or
        -not [string]::Equals($identity.Groups['name'].Value, $ResourceName, $comparison)) {
        throw "Resource ID does not identify requested Microsoft.App/$ResourceType '$ResourceName' in resource group '$GroupName'; no resources were changed."
    }
    return $identity.Groups['subscription'].Value
}

function Get-ResourceEnvironmentId {
    param([object]$Properties)
    $legacy = $Properties.managedEnvironmentId
    $current = $Properties.environmentId
    if (($null -ne $legacy -and $legacy -isnot [string]) -or
        ($null -ne $current -and $current -isnot [string])) {
        throw "Environment relationship must be a string; deletion cannot continue."
    }
    if ($legacy -and $current -and
        -not [string]::Equals($legacy, $current, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Conflicting environment relationship fields; deletion cannot continue."
    }
    if ($legacy) { return $legacy }
    return $current
}

$appJson = az containerapp show --resource-group $ResourceGroup --name $AppName --output json
if ($LASTEXITCODE -ne 0) { throw "Container App lookup failed; no resources were changed." }
$app = $appJson | ConvertFrom-Json
$environmentJson = az containerapp env show --resource-group $ResourceGroup --name $EnvironmentName --output json
if ($LASTEXITCODE -ne 0) { throw "Environment lookup failed; no resources were changed." }
$env = $environmentJson | ConvertFrom-Json
$appSubscription = Get-ValidatedResourceSubscription -ResourceId $app.id -ResourceType 'containerApps' -ResourceName $AppName -GroupName $ResourceGroup
$environmentSubscription = Get-ValidatedResourceSubscription -ResourceId $env.id -ResourceType 'managedEnvironments' -ResourceName $EnvironmentName -GroupName $ResourceGroup
if (-not [string]::Equals($appSubscription, $environmentSubscription, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "App and environment resource IDs identify different subscriptions; no resources were changed."
}
$containerEnvironmentId = Get-ResourceEnvironmentId -Properties $app.properties
if ($containerEnvironmentId -isnot [string] -or
    $app.tags.purpose -ne "public-demo" -or $app.tags.application -ne "pulse-xi" -or
    -not [string]::Equals($containerEnvironmentId, $env.id, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "App identity, tags or environment relationship do not match this demo; no resources were changed."
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
Write-Host "Named Container App '$AppName' deletion succeeded; environment deletion has not been requested."

if ($DeleteEnvironment) {
    $environmentId = $env.id.ToLowerInvariant()
    $appsJson = (az containerapp list --resource-group $ResourceGroup --output json) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw "Remaining-app inventory failed; the environment was retained. The named app was already deleted." }
    if (-not $appsJson -or -not $appsJson.TrimStart().StartsWith('[')) {
        throw "Remaining-app inventory is not a JSON array; environment retained."
    }
    $apps = $appsJson | ConvertFrom-Json
    if (($null -eq $apps -or @($apps).Count -eq 0) -and $appsJson.Trim() -notmatch '^\[\s*\]$') {
        throw "Remaining-app inventory contains no usable records; environment retained."
    }
    foreach ($candidate in $apps) {
        $candidateEnvironment = Get-ResourceEnvironmentId -Properties $candidate.properties
        [void](Get-ValidatedResourceIdentity -ResourceId $candidateEnvironment -ResourceType 'managedEnvironments')
    }
    $remaining = @($apps | Where-Object {
        $id = Get-ResourceEnvironmentId -Properties $_.properties
        $id -and $id.ToLowerInvariant() -eq $environmentId
    })
    if ($remaining.Count -gt 0) { throw "Environment still contains other apps ($($remaining.name -join ', ')); it was retained." }
    $environmentConfirmation = Read-Host "Type DELETE ENVIRONMENT $EnvironmentName to delete this now-empty demo environment"
    if ($environmentConfirmation -cne "DELETE ENVIRONMENT $EnvironmentName") { throw "Confirmation did not match; environment retained." }
    az containerapp env delete --resource-group $ResourceGroup --name $EnvironmentName --yes
    if ($LASTEXITCODE -ne 0) { throw "Environment deletion failed; inspect Azure state before retrying." }
}
