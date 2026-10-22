"""Regression checks for the public and protected route inventory in issue #23."""
import json

from fastapi.testclient import TestClient

from app.main import app


def test_openapi_classifies_public_writes_and_protected_operations(monkeypatch, tmp_path):
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'matches.sqlite'))
    monkeypatch.delenv('PULSE_IMPORT_TOKEN', raising=False)
    monkeypatch.delenv('PULSE_RUNTIME_TOKEN', raising=False)
    monkeypatch.delenv('PULSE_RUNTIME_TOKENS', raising=False)
    schema = app.openapi()
    operations = {
        (path, method): operation
        for path, item in schema['paths'].items()
        for method, operation in item.items()
        if method in {'get', 'post', 'put', 'patch', 'delete'}
    }

    # These intentionally public operations produce deterministic output but
    # do not mutate persisted application state.
    assert ('/api/matches/generate', 'post') in operations
    assert ('/api/matches/{match_id}/recap', 'post') in operations
    assert TestClient(app).post('/api/matches/generate', json={'seed': 2}).status_code == 200

    # Every stateful, owner-scoped route must fail closed without credentials.
    for path, item in schema['paths'].items():
        if not path.startswith('/api/sandbox/'):
            continue
        for method, operation in item.items():
            if method not in {'get', 'post', 'put', 'patch', 'delete'}:
                continue
            # FastAPI records the Header dependency under its Python parameter name.
            assert any(p.get('name') == 'authorization' for p in operation.get('parameters', [])), (path, method)
    # Missing credentials and unconfigured operator credentials both fail closed.
    assert TestClient(app).get('/api/sandbox/versions').status_code in {403, 503}
    monkeypatch.setenv('PULSE_RUNTIME_TOKEN', 'r' * 32)
    assert TestClient(app).get('/api/sandbox/versions').status_code == 403


def test_mutating_import_and_lifecycle_routes_require_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'matches.sqlite'))
    monkeypatch.delenv('PULSE_IMPORT_TOKEN', raising=False)
    monkeypatch.delenv('PULSE_ENABLE_LOCAL_DATA_ADMIN', raising=False)
    client = TestClient(app, base_url='http://127.0.0.1')
    assert client.post('/api/data-hub/import', json={}).status_code == 503
    monkeypatch.setenv('PULSE_IMPORT_TOKEN', 'x' * 32)
    # Import auth alone does not authorize destructive lifecycle actions.
    assert client.post('/api/data-hub/matches/any/lifecycle', json={}).status_code == 403
    monkeypatch.setenv('PULSE_ENABLE_LOCAL_DATA_ADMIN', '1')
    forwarded = TestClient(app, base_url='http://127.0.0.1', client=('127.0.0.1', 55000))
    response = forwarded.post('/api/data-hub/matches/any/lifecycle', json={},
                              headers={'Authorization': 'Bearer ' + 'x' * 32,
                                       'X-Forwarded-For': '127.0.0.1'})
    assert response.status_code == 403


def test_public_match_websocket_is_read_only_and_sandbox_socket_requires_auth_frame(monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice': 'a' * 32}))
    client = TestClient(app)
    with client.websocket_connect('/ws/matches/comeback-1107') as socket:
        assert socket.receive_json()['kind'] == 'snapshot'
        assert socket.receive_json()['kind'] == 'event'
    from starlette.websockets import WebSocketDisconnect
    with client.websocket_connect('/api/sandbox/sessions/missing/observe') as socket:
        socket.send_text('{"token":"wrong"}')
        try:
            message = socket.receive_json()
        except WebSocketDisconnect:
            message = None
        assert message is None, 'unauthorized runtime socket must close without sending state'


def test_export_is_bounded_and_download_safe():
    client = TestClient(app)
    assert client.post('/api/matches/comeback-1107/recap', params={'at_second': 5401}).status_code == 422
    response = client.get('/api/matches/comeback-1107/analysis-export', params={
        'at_second': 5400, 'category': 'events', 'format': 'csv'})
    assert response.status_code == 200
    assert 'text/csv' in response.headers['content-type']
