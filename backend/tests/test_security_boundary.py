import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import LocalStaticFiles, RequestBoundary


@pytest.mark.parametrize('configured_token', [None, ''])
def test_trace_reads_fail_closed_without_admin(monkeypatch, configured_token):
    from app import main
    if configured_token is None:
        monkeypatch.delenv('PULSE_FOUNDRY_ADMIN_TOKEN', raising=False)
    else:
        monkeypatch.setenv('PULSE_FOUNDRY_ADMIN_TOKEN', configured_token)
    monkeypatch.setattr(main, 'TRACES', [{'trace_id': 'synthetic-audit-sentinel'}])
    with TestClient(app) as client:
        response = client.get('/api/agent-traces')
    assert response.status_code == 503
    assert 'synthetic-audit-sentinel' not in response.text


def test_trace_reads_require_current_admin_and_hide_retained_records(monkeypatch):
    from app import main
    token = 'test-only-foundry-admin-token'
    records = [{'trace_id': 'synthetic-audit-sentinel'}]
    monkeypatch.setenv('PULSE_FOUNDRY_ADMIN_TOKEN', token)
    monkeypatch.setattr(main, 'TRACES', records)
    with TestClient(app) as client:
        for headers in ({}, {'X-Admin-Token': 'incorrect'}, {'X-Admin-Token': b'\xff'}):
            response = client.get('/api/agent-traces', headers=headers)
            assert response.status_code == 403
            assert 'synthetic-audit-sentinel' not in response.text
        response = client.get('/api/agent-traces', headers={'X-Admin-Token': token})
        assert response.status_code == 200 and response.json() == records
        monkeypatch.delenv('PULSE_FOUNDRY_ADMIN_TOKEN')
        response = client.get('/api/agent-traces', headers={'X-Admin-Token': token})
        assert response.status_code == 503
        assert 'synthetic-audit-sentinel' not in response.text


@pytest.mark.parametrize('path', [r'\\untrusted.invalid\share\file', r'C:\secret', r'\??\UNC\host\share'])
def test_windows_paths_rejected_before_filesystem_io(tmp_path, monkeypatch, path):
    static = LocalStaticFiles(directory=tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError('unsafe path reached filesystem resolver')
    monkeypatch.setattr('os.path.realpath', forbidden)
    assert static.lookup_path(path) == ('', None)


def test_local_assets_still_resolve(tmp_path):
    (tmp_path / 'notice.txt').write_text('notice')
    assert LocalStaticFiles(directory=tmp_path).lookup_path('notice.txt')[1] is not None


def test_bad_host_and_oversized_or_invalid_json():
    with TestClient(app) as client:
        assert client.get('/health', headers={'host': 'local/path?query'}).status_code == 400
        assert client.post('/api/matches/generate', content=b'x' * 2_000_001).status_code == 413
        assert client.post('/api/matches/generate', content='{', headers={'content-type': 'application/json'}).status_code == 422
        assert client.post('/api/matches/generate', json={'seed': 0}).status_code == 200


def test_chunked_body_limit_and_boundary_without_external_network():
    async def exercise(parts, expected, path='/api/test'):
        messages = []
        async def downstream(scope, receive, send):
            assert (await receive())['body'] == b'abcd'
            messages.append({'status': 204})
        chunks = iter([{'type': 'http.request', 'body': p, 'more_body': i < len(parts)-1} for i,p in enumerate(parts)])
        async def receive(): return next(chunks)
        async def send(message): messages.append(message)
        await RequestBoundary(downstream, max_body_bytes=4)({'type': 'http', 'method': 'POST', 'path': path, 'headers': []}, receive, send)
        assert messages[0]['status'] == expected
    asyncio.run(exercise([b'ab', b'cd'], 204))
    asyncio.run(exercise([b'abc', b'de'], 413))
    asyncio.run(exercise([b'abcd'], 400, path='@untrusted.invalid'))
