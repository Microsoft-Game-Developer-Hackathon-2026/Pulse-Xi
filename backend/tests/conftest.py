"""Tests never inherit developer stores, runtime jobs or paid-provider settings."""
import os

import pytest


@pytest.fixture(autouse=True)
def isolated_application_environment(tmp_path, monkeypatch):
    # Individual authorization/driver tests explicitly provision their own values
    # after this baseline. Do not let TestClient lifespan resume a developer job.
    for key in list(os.environ):
        if key.startswith(('PULSE_', 'FOUNDRY_')):
            monkeypatch.delenv(key)
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'test-library.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(tmp_path / 'test-runtime.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.setenv('PULSE_ENABLE_FOUNDRY', 'false')
