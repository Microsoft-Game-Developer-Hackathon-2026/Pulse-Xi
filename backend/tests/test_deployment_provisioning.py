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
& $env:PROVISION_TEST_SCRIPT -ResourceGroup unused -Image $env:PROVISION_TEST_IMAGE
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
