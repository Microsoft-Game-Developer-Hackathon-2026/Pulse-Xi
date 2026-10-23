"""Run teardown against an in-process fake Azure CLI; never contact Azure."""
import base64
import os
from pathlib import Path
import shutil
import subprocess

import pytest


POWERSHELL = shutil.which('pwsh') or shutil.which('powershell')
SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'azure' / 'teardown.ps1'
SUBSCRIPTION = '11111111-2222-3333-4444-555555555555'
ARM_ROOT = f'/subscriptions/{SUBSCRIPTION}/resourceGroups/unused/providers/Microsoft.App'
APP_ID = f'{ARM_ROOT}/containerApps/demo'
ENVIRONMENT_ID = f'{ARM_ROOT}/managedEnvironments/demo-env'
INVALID_IDENTITIES = {
    'wrong-app-name': (APP_ID.replace('/demo', '/other-demo'), ENVIRONMENT_ID),
    'wrong-env-name': (APP_ID, ENVIRONMENT_ID.replace('/demo-env', '/other-env')),
    'wrong-app-group': (APP_ID.replace('/unused/', '/other-group/'), ENVIRONMENT_ID),
    'wrong-env-group': (APP_ID, ENVIRONMENT_ID.replace('/unused/', '/other-group/')),
    'wrong-app-provider': (APP_ID.replace('Microsoft.App', 'Microsoft.Compute'), ENVIRONMENT_ID),
    'wrong-env-provider': (APP_ID, ENVIRONMENT_ID.replace('Microsoft.App', 'Microsoft.Compute')),
    'wrong-app-type': (APP_ID.replace('/containerApps/', '/managedEnvironments/'), ENVIRONMENT_ID),
    'wrong-env-type': (APP_ID, ENVIRONMENT_ID.replace('/managedEnvironments/', '/containerApps/')),
    'missing-app-subscription-segment': (APP_ID.replace(f'/subscriptions/{SUBSCRIPTION}', ''), ENVIRONMENT_ID),
    'missing-env-subscription-value': (APP_ID, ENVIRONMENT_ID.replace(SUBSCRIPTION, '')),
    'malformed-app-subscription': (APP_ID.replace(SUBSCRIPTION, 'invalid'), ENVIRONMENT_ID),
    'malformed-env-subscription': (APP_ID, ENVIRONMENT_ID.replace(SUBSCRIPTION, 'invalid')),
    'missing-app-group-segment': (APP_ID.replace('/resourceGroups/unused', ''), ENVIRONMENT_ID),
    'missing-env-provider-segment': (APP_ID, ENVIRONMENT_ID.replace('/providers/Microsoft.App', '')),
    'extra-app-prefix': ('/other' + APP_ID, ENVIRONMENT_ID),
    'extra-env-suffix': (APP_ID, ENVIRONMENT_ID + '/child/other'),
    'app-terminal-newline': (APP_ID + '\n', ENVIRONMENT_ID),
    'different-subscriptions': (APP_ID, ENVIRONMENT_ID.replace(SUBSCRIPTION, 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')),
}


@pytest.mark.skipif(not POWERSHELL, reason='PowerShell is required for teardown guard tests')
@pytest.mark.parametrize('scenario,allowed', [
    ('empty', True), ('other-environment', True),
    ('list-error', False), ('list-no-output', False), ('list-null', False),
    ('list-object', False), ('list-malformed', False), ('list-incomplete', False),
    ('list-null-entry', False), ('list-array-entry', False),
    ('remaining-app', False), ('app-show-error', False), ('env-show-error', False),
    ('missing-target-ids', False),
    ('wrong-tags', False), ('wrong-environment', False), ('app-delete-error', False),
    ('mixed-case-identities', True),
    ('contradictory-target-environments', False), ('matching-target-environments', True),
    ('managed-environment-only', True), ('remaining-app-contradictory-environments', False),
    ('list-mixed-null-entry', False), ('list-mixed-array-entry', False),
    ('list-malformed-environment-id', False),
    ('wrong-env-tags', False), ('wrong-app-confirmation', False),
    ('wrong-env-confirmation', False), ('env-delete-error', False),
    *((scenario, False) for scenario in INVALID_IDENTITIES),
])
def test_teardown_requires_successful_complete_inventory_before_environment_deletion(scenario, allowed):
    command = r'''
function az {
    $global:LASTEXITCODE = 0
    $operation = $args -join ' '
    if ($operation -like 'containerapp show *') {
        if ($env:TEARDOWN_TEST_CASE -eq 'app-show-error') { $global:LASTEXITCODE = 17 }
        if ($env:TEARDOWN_TEST_CASE -eq 'missing-target-ids') {
            return '{"tags":{"purpose":"public-demo","application":"pulse-xi"},"properties":{}}'
        }
        $tag = if ($env:TEARDOWN_TEST_CASE -eq 'wrong-tags') { 'other' } else { 'pulse-xi' }
        $environment = if ($env:TEARDOWN_TEST_CASE -eq 'wrong-environment') { '/env/unrelated' } else { $env:TEARDOWN_TEST_RELATIONSHIP }
        $properties = @{environmentId=$environment}
        if ($env:TEARDOWN_TEST_CASE -eq 'contradictory-target-environments') {
            $properties.managedEnvironmentId=$environment
            $properties.environmentId=$environment + '-other'
        }
        if ($env:TEARDOWN_TEST_CASE -eq 'matching-target-environments') {
            $properties.managedEnvironmentId=$environment.ToUpperInvariant()
        }
        if ($env:TEARDOWN_TEST_CASE -eq 'managed-environment-only') {
            $properties=@{managedEnvironmentId=$environment}
        }
        return (@{id=$env:TEARDOWN_TEST_APP_ID; tags=@{purpose='public-demo'; application=$tag};
            properties=$properties} | ConvertTo-Json -Depth 4 -Compress)
    }
    if ($operation -like 'containerapp env show *') {
        if ($env:TEARDOWN_TEST_CASE -eq 'env-show-error') { $global:LASTEXITCODE = 17 }
        if ($env:TEARDOWN_TEST_CASE -eq 'missing-target-ids') {
            return '{"tags":{"purpose":"public-demo","application":"pulse-xi"}}'
        }
        $tag = if ($env:TEARDOWN_TEST_CASE -eq 'wrong-env-tags') { 'other' } else { 'pulse-xi' }
        return (@{id=$env:TEARDOWN_TEST_ENVIRONMENT_ID; tags=@{purpose='public-demo'; application=$tag}} | ConvertTo-Json -Compress)
    }
    if ($operation -like 'containerapp list *') {
        switch ($env:TEARDOWN_TEST_CASE) {
            'list-error' { $global:LASTEXITCODE=17; return '[]' }
            'list-no-output' { return }
            'list-null' { return 'null' }
            'list-object' { return '{}' }
            'list-malformed' { return '[invalid]' }
            'list-incomplete' { return '[{"name":"unknown"}]' }
            'list-null-entry' { return '[null]' }
            'list-array-entry' { return '[[]]' }
            'list-malformed-environment-id' { return '[{"name":"unknown","properties":{"environmentId":"/env/invalid"}}]' }
            'list-mixed-null-entry' { return ('[null,{"name":"unrelated","properties":{"environmentId":"' + $env:TEARDOWN_TEST_ENVIRONMENT_ID + '-other"}}]') }
            'list-mixed-array-entry' { return ('[[],{"name":"unrelated","properties":{"environmentId":"' + $env:TEARDOWN_TEST_ENVIRONMENT_ID + '-other"}}]') }
            'remaining-app-contradictory-environments' {
                return (ConvertTo-Json -InputObject @(@{name='teammate'; properties=@{
                    managedEnvironmentId=$env:TEARDOWN_TEST_ENVIRONMENT_ID + '-other';
                    environmentId=$env:TEARDOWN_TEST_ENVIRONMENT_ID}}) -Depth 4 -Compress)
            }
            'remaining-app' { return (ConvertTo-Json -InputObject @(@{name='teammate'; properties=@{managedEnvironmentId=$env:TEARDOWN_TEST_ENVIRONMENT_ID}}) -Depth 4 -Compress) }
            'other-environment' { return (ConvertTo-Json -InputObject @(@{name='unrelated'; properties=@{environmentId=$env:TEARDOWN_TEST_ENVIRONMENT_ID + '-other'}}) -Depth 4 -Compress) }
            default { return '[]' }
        }
    }
    if ($operation -like 'containerapp delete *') {
        Write-Output 'OFFLINE_APP_DELETE'
        if ($env:TEARDOWN_TEST_CASE -eq 'app-delete-error') { $global:LASTEXITCODE=17 }
        return
    }
    if ($operation -like 'containerapp env delete *') {
        Write-Output 'OFFLINE_ENVIRONMENT_DELETE'
        if ($env:TEARDOWN_TEST_CASE -eq 'env-delete-error') { $global:LASTEXITCODE=17 }
        return
    }
    throw "Unexpected fake Azure operation: $operation"
}
function Read-Host {
    param([string]$Prompt)
    [Console]::WriteLine('OFFLINE_CONFIRMATION')
    if ($Prompt -like 'Type DELETE APP *' -and $env:TEARDOWN_TEST_CASE -eq 'wrong-app-confirmation') { return 'NO' }
    if ($Prompt -like 'Type DELETE ENVIRONMENT *' -and $env:TEARDOWN_TEST_CASE -eq 'wrong-env-confirmation') { return 'NO' }
    if ($Prompt -like 'Type DELETE APP *') { return 'DELETE APP demo' }
    if ($Prompt -like 'Type DELETE ENVIRONMENT *') { return 'DELETE ENVIRONMENT demo-env' }
    throw 'Unexpected confirmation prompt'
}
try {
    & $env:TEARDOWN_TEST_SCRIPT -ResourceGroup unused -AppName demo -EnvironmentName demo-env -ConfirmTarget -DeleteEnvironment
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
'''
    environment = os.environ.copy()
    environment.update(TEARDOWN_TEST_SCRIPT=str(SCRIPT), TEARDOWN_TEST_CASE=scenario)
    app_id, environment_id = INVALID_IDENTITIES.get(scenario, (APP_ID, ENVIRONMENT_ID))
    if scenario == 'mixed-case-identities':
        app_id, environment_id = app_id.upper(), environment_id.upper()
    # Keep the relationship consistent with even an invalid returned environment
    # ID: matching two wrong IDs must not authorize the requested target deletion.
    relationship = environment_id.lower() if scenario == 'mixed-case-identities' else environment_id
    environment.update(TEARDOWN_TEST_APP_ID=app_id, TEARDOWN_TEST_ENVIRONMENT_ID=environment_id,
                       TEARDOWN_TEST_RELATIONSHIP=relationship)
    result = subprocess.run([POWERSHELL, '-NoLogo', '-NoProfile', '-NonInteractive',
        '-EncodedCommand', base64.b64encode(command.encode('utf-16le')).decode('ascii')],
        env=environment, capture_output=True, text=True, timeout=20)
    output = result.stdout + result.stderr
    assert 'Unexpected fake Azure operation' not in output, output
    assert 'Unexpected confirmation prompt' not in output, output
    if scenario == 'env-delete-error':
        assert result.returncode != 0, output
        assert 'OFFLINE_ENVIRONMENT_DELETE' in output, output
        assert 'Environment deletion failed' in output, output
    elif allowed:
        assert result.returncode == 0, output
        assert 'OFFLINE_ENVIRONMENT_DELETE' in output, output
    else:
        assert result.returncode != 0, output
        assert 'OFFLINE_ENVIRONMENT_DELETE' not in output, output
    if scenario in {'app-show-error', 'env-show-error', 'wrong-tags', 'wrong-environment', 'missing-target-ids',
                    'wrong-env-tags', 'wrong-app-confirmation', 'contradictory-target-environments'}:
        assert 'OFFLINE_APP_DELETE' not in output, output
    if scenario in INVALID_IDENTITIES or scenario == 'contradictory-target-environments':
        assert 'OFFLINE_APP_DELETE' not in output, output
        assert 'OFFLINE_ENVIRONMENT_DELETE' not in output, output
        assert 'OFFLINE_CONFIRMATION' not in output, output
    if scenario in {'wrong-env-confirmation', 'remaining-app-contradictory-environments',
                    'list-mixed-null-entry', 'list-mixed-array-entry', 'list-malformed-environment-id'}:
        assert 'OFFLINE_APP_DELETE' in output, output
        assert "Named Container App 'demo' deletion succeeded" in output, output
    if scenario == 'app-delete-error':
        assert 'deletion succeeded' not in output, output
