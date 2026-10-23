"""Exercise provisioning input validation with every Azure call replaced offline."""
import base64
import os
from pathlib import Path
import shutil
import subprocess

import pytest


POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
PROVISION = Path(__file__).resolve().parents[2] / "scripts" / "azure" / "provision.ps1"
DIGEST = "a" * 64


@pytest.mark.skipif(not POWERSHELL, reason="PowerShell is required for provisioning guard tests")
@pytest.mark.parametrize("image,valid", [
    (f"ghcr.io/example/pulse-xi-demo@sha256:{DIGEST}", True),
    ("ghcr.io/example/pulse-xi-demo:latest", False),
    (f"ghcr.io/example/pulse-xi-demo@sha256:{DIGEST}\n", False),
    ("ghcr.io/example/pulse-xi-demo:" + "b" * 40, False),
    ("ghcr.io/example/pulse-xi-demo@sha256:" + "a" * 63, False),
    ("ghcr.io/example/pulse-xi-demo@sha256:" + "g" * 64, False),
    ("ghcr.io/example/pulse-xi-demo@sha256:" + "A" * 64, False),
    (f"https://ghcr.io/example/pulse-xi-demo@sha256:{DIGEST}", False),
    (f"ghcr.io/user:password@example/pulse-xi-demo@sha256:{DIGEST}", False),
    (f"ghcr.io/example/pulse-xi-demo@sha256:{DIGEST}?token=invalid", False),
])
def test_provision_requires_digest_before_contacting_azure(image, valid):
    # The function shadows any real Azure executable, including for valid input.
    # Reaching it proves the valid digest passed validation without cloud access.
    command = """
function az { throw 'OFFLINE_AZURE_SENTINEL' }
try {
    & $env:PROVISION_TEST_SCRIPT -ResourceGroup unused -Image $env:PROVISION_TEST_IMAGE
} catch {
    # Windows PowerShell otherwise wraps error records in width-dependent CLIXML.
    # Emit the actual exception message so assertions test the guard on both hosts.
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
"""
    encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
    environment = os.environ.copy()
    environment.update(PROVISION_TEST_SCRIPT=str(PROVISION), PROVISION_TEST_IMAGE=image)
    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        env=environment, capture_output=True, text=True, timeout=20,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    if valid:
        assert "OFFLINE_AZURE_SENTINEL" in output, output
        assert "tags and credentials are not accepted" not in output, output
    else:
        assert "tags and credentials are not accepted" in output, output
        assert "OFFLINE_AZURE_SENTINEL" not in output, output


def test_workflow_revision_names_allow_numeric_shas_and_distinguish_retries():
    import re
    import yaml

    # ACA requires an alphabetic prefix; revision contents are immutable.
    workflow_path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy-azure.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    suffix = next(step["env"]["REVISION_SUFFIX"] for step in workflow["jobs"]["deploy"]["steps"]
                  if "REVISION_SUFFIX" in step.get("env", {}))
    names = []
    for run_id, attempt in [(123, 1), (123, 2), (456, 1)]:
        name = suffix.replace("${{ github.sha }}", "45eabc4ca058a47241e58ecc42c8bc49980eaf92")
        name = name.replace("${{ github.run_id }}", str(run_id)).replace("${{ github.run_attempt }}", str(attempt))
        assert 1 <= len(name) <= 64
        assert re.fullmatch(r"[a-z](?:[a-z0-9-]*[a-z0-9])?", name), name
        assert "--" not in name
        names.append(name)
    assert len(set(names)) == len(names), "Deployments/retries must not reuse an immutable revision name"
