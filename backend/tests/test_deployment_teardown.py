"""Run teardown against an in-process fake Azure CLI; never contact Azure."""
import base64
import os
from pathlib import Path
import shutil
import subprocess

import pytest


POWERSHELL = shutil.which('pwsh') or shutil.which('powershell')
SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'azure' / 'teardown.ps1'


@pytest.mark.skipif(not POWERSHELL, reason='PowerShell is required for teardown guard tests')
@pytest.mark.parametrize('scenario,allowed', [
    ('empty', True), ('other-environment', True),
    ('list-error', False), ('list-no-output', False), ('list-null', False),
    ('list-object', False), ('list-malformed', False), ('list-incomplete', False),
    ('list-null-entry', False), ('list-array-entry', False),
    ('remaining-app', False), ('app-show-error', False), ('env-show-error', False),
    ('wrong-tags', False), ('wrong-environment', False), ('app-delete-error', False),
])
def test_teardown_requires_successful_complete_inventory_before_environment_deletion(scenario, allowed):
    command = r'''
function az {
    $global:LASTEXITCODE = 0
    $operation = $args -join ' '
    if ($operation -like 'containerapp show *') {
        if ($env:TEARDOWN_TEST_CASE -eq 'app-show-error') { $global:LASTEXITCODE = 17 }
        $tag = if ($env:TEARDOWN_TEST_CASE -eq 'wrong-tags') { 'other' } else { 'pulse-xi' }
        $environment = if ($env:TEARDOWN_TEST_CASE -eq 'wrong-environment') { '/env/unrelated' } else { '/env/demo' }
        return (@{id='/app/demo'; tags=@{purpose='public-demo'; application=$tag};
            properties=@{environmentId=$environment}} | ConvertTo-Json -Depth 4 -Compress)
    }
    if ($operation -like 'containerapp env show *') {
        if ($env:TEARDOWN_TEST_CASE -eq 'env-show-error') { $global:LASTEXITCODE = 17 }
        return '{"id":"/env/demo","tags":{"purpose":"public-demo","application":"pulse-xi"}}'
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
            'remaining-app' { return '[{"name":"teammate","properties":{"managedEnvironmentId":"/env/demo"}}]' }
            'other-environment' { return '[{"name":"unrelated","properties":{"environmentId":"/env/other"}}]' }
            default { return '[]' }
        }
    }
    if ($operation -like 'containerapp delete *') {
        Write-Output 'OFFLINE_APP_DELETE'
        if ($env:TEARDOWN_TEST_CASE -eq 'app-delete-error') { $global:LASTEXITCODE=17 }
        return
    }
    if ($operation -like 'containerapp env delete *') { Write-Output 'OFFLINE_ENVIRONMENT_DELETE'; return }
    throw "Unexpected fake Azure operation: $operation"
}
function Read-Host {
    param([string]$Prompt)
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
    result = subprocess.run([POWERSHELL, '-NoLogo', '-NoProfile', '-NonInteractive',
        '-EncodedCommand', base64.b64encode(command.encode('utf-16le')).decode('ascii')],
        env=environment, capture_output=True, text=True, timeout=20)
    output = result.stdout + result.stderr
    if allowed:
        assert result.returncode == 0, output
        assert 'OFFLINE_ENVIRONMENT_DELETE' in output, output
    else:
        assert result.returncode != 0, output
        assert 'OFFLINE_ENVIRONMENT_DELETE' not in output, output
    if scenario in {'app-show-error', 'env-show-error', 'wrong-tags', 'wrong-environment'}:
        assert 'OFFLINE_APP_DELETE' not in output, output
