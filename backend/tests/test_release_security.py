"""Release boundary guards complement per-resource ownership/error tests."""
import re

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app
from app.sandbox.api import require_operator, router


def test_every_runtime_rest_operation_authenticates_before_access(monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.delenv('PULSE_RUNTIME_TOKENS', raising=False)
    monkeypatch.setenv('PULSE_RUNTIME_TOKEN', 'release-test-operator-token-at-least-32-characters')
    checked = 0
    with TestClient(app) as client:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue  # WebSocket first-frame auth/revocation has separate tests.
            assert any(dep.call is require_operator for dep in route.dependant.dependencies), route.path
            path = re.sub(r'\{[^}]+\}', 'not-an-owned-object', route.path)
            for method in route.methods:
                response = client.request(method, path)
                assert response.status_code == 403, (method, path, response.text)
                assert response.headers['cache-control'] == 'no-store', path
                checked += 1
    assert checked >= 35


def test_cors_allowlist_does_not_authorize_runtime_access(monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.delenv('PULSE_RUNTIME_TOKENS', raising=False)
    monkeypatch.setenv('PULSE_RUNTIME_TOKEN', 'release-test-operator-token-at-least-32-characters')
    with TestClient(app) as client:
        for origin, status in [('http://127.0.0.1:5173', 200), ('https://untrusted.invalid', 400)]:
            response = client.options('/api/sandbox/scenarios', headers={
                'Origin': origin, 'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Authorization'})
            assert response.status_code == status
            assert response.headers.get('access-control-allow-origin') == (origin if status == 200 else None)
        response = client.get('/api/sandbox/scenarios', headers={'Origin': 'http://127.0.0.1:5173'})
        assert response.status_code == 403
        assert response.headers['cache-control'] == 'no-store'


def test_privileged_traces_never_allow_storage_in_success_or_error(monkeypatch):
    from app import main
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.setattr(main, 'TRACES', [{'trace_id': 'release-test-private-record'}])
    with TestClient(app) as client:
        for token, headers, status in [('', {}, 503), ('release-admin', {}, 403),
            ('release-admin', {'X-Admin-Token': 'wrong'}, 403),
            ('release-admin', {'X-Admin-Token': 'release-admin'}, 200)]:
            monkeypatch.setenv('PULSE_FOUNDRY_ADMIN_TOKEN', token)
            response = client.get('/api/agent-traces', headers=headers)
            assert response.status_code == status
            assert response.headers.get('cache-control') == 'no-store'
            assert ('release-test-private-record' in response.text) is (status == 200)
