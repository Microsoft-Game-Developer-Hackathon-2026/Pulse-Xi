"""Authorization-only tests: hosted providers must never run."""
import pytest
from fastapi.testclient import TestClient
from app import main


@pytest.mark.parametrize('credential', [None, 'wrong', b'\xff'])
def test_privileged_command_rejects_malformed_credentials_without_provider(monkeypatch, credential):
    monkeypatch.setattr(main, 'configured', lambda: True)
    monkeypatch.setenv('PULSE_FOUNDRY_ADMIN_TOKEN', 'test-only-foundry-token')
    async def forbidden(*args):
        pytest.fail('an unauthorized request reached the provider boundary')
    monkeypatch.setattr(main, 'run_specialists', forbidden)
    headers = {} if credential is None else {'X-Admin-Token': credential}
    assert TestClient(main.app).post('/api/insights/unknown/agent-run', headers=headers).status_code == 403


def test_privileged_command_retains_authorized_dispatch_and_revokes(monkeypatch, tmp_path):
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'matches.sqlite'))
    monkeypatch.setattr(main, 'configured', lambda: True)
    token = 'test-only-foundry-token'
    monkeypatch.setenv('PULSE_FOUNDRY_ADMIN_TOKEN', token)
    calls = []
    async def local_boundary(match, events, insight):
        calls.append(insight.insight_id)
        return {'provider_called': False, 'authorization_test': True}
    monkeypatch.setattr(main, 'run_specialists', local_boundary)
    match, events = main.stored('comeback')
    insight = main.insights_for(match, events)[0]
    client = TestClient(main.app)
    path = f'/api/insights/{insight.insight_id}/agent-run'
    assert client.post(path, headers={'X-Admin-Token': token}).json()['authorization_test']
    assert calls == [insight.insight_id]
    monkeypatch.delenv('PULSE_FOUNDRY_ADMIN_TOKEN')
    assert client.post(path, headers={'X-Admin-Token': token}).status_code == 403
    assert calls == [insight.insight_id]
