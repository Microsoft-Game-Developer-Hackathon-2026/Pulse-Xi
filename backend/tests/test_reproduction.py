"""Portable exports use the real engine; observational context is not an attestation."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.sandbox import storage, control, reproduction
from app.sandbox.engine import canonical
from app.sandbox.manifest import verify_manifest
from app.sandbox.models import Command
from app.sandbox.experiments import verify_bundle
from test_authoritative_engine import database, runtime

TOKEN = 'reproduction-alice-token-at-least-32-characters'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}
BOB = {'Authorization': 'Bearer bob-reproduction-token-at-least-32-characters'}


@pytest.fixture
def client(database, monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice': TOKEN, 'bob': BOB['Authorization'][7:]}))
    return TestClient(app)


@pytest.fixture
def manifest(database):
    root = runtime()
    saved = storage.mutate('alice', root.session_id, Command(operation_id='save', expected_revision=0, kind='checkpoint'))
    child = storage.create_session('alice', 'fork', checkpoint_id=saved.checkpoint_id, expected_revision=1)
    storage.mutate('alice', child.session_id, Command(operation_id='press', expected_revision=1, kind='intervene',
        requested_tick=0, team_id='home', field='pressing', value=100))
    storage.mutate('alice', child.session_id, Command(operation_id='step', expected_revision=2, kind='step', ticks=120))
    return storage.manifest('alice', child.session_id)


def test_runtime_export_owner_auth_versions_and_independent_cli(client, manifest, tmp_path):
    path = f'/api/sandbox/sessions/{manifest.session_id}/reproduction'
    response = client.get(path, headers=HEADERS)
    assert response.status_code == 200 and response.headers['Cache-Control'] == 'no-store'
    data = response.json()
    assert data['archive_version'] == 'runtime-reproduction/1'
    assert data['manifest'] == manifest.model_dump(mode='json')
    expected_revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    assert data['provenance']['git_revision'] == expected_revision
    assert isinstance(data['provenance']['working_tree_dirty'], bool)
    text = canonical(data)
    for private in [TOKEN, 'PULSE_RUNTIME_TOKENS', str(Path.cwd()), 'Authorization']:
        assert private not in text
    assert client.get(path).status_code == 403
    assert client.get(path, headers=BOB).status_code == 404
    assert client.post('/api/sandbox/verify', headers=HEADERS, json=data).json()['verified']
    # Reordered JSON, a fresh verifier process and a nonexistent runtime DB.
    archive = tmp_path / 'runtime.json'
    archive.write_text(json.dumps(dict(reversed(list(data.items()))), indent=2), encoding='utf-8')
    isolated = {**os.environ, 'PULSE_RUNTIME_DB_PATH': str(tmp_path / 'unused-runtime.sqlite'),
                'PULSE_DB_PATH': str(tmp_path / 'unused-library.sqlite')}
    result = subprocess.run([sys.executable, '-m', 'app.sandbox.verify_manifest', str(archive)], capture_output=True, text=True, env=isolated)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['verified']
    assert not (tmp_path / 'unused-runtime.sqlite').exists()
    assert not (tmp_path / 'unused-library.sqlite').exists()


def test_observational_context_is_unsigned_and_not_deterministic_input(manifest, monkeypatch):
    first = reproduction.runtime_reproduction(manifest).model_dump(mode='json')
    first['provenance']['git_revision'] = 'f' * 40
    first['provenance']['working_tree_dirty'] = False
    first['provenance']['python_version'] = '3.99.1'
    # Replay validity says nothing about the authenticity of those claims.
    assert verify_manifest(reproduction.read_runtime(canonical(first).encode())).verified
    def unavailable(*args, **kwargs): raise OSError('git unavailable')
    monkeypatch.setattr(reproduction.subprocess, 'run', unavailable)
    observed = reproduction.execution_provenance()
    assert observed.git_revision is None and observed.working_tree_dirty is None


def test_parent_checkout_is_not_misreported_as_source_provenance(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setattr(reproduction.subprocess, 'run', lambda *args, **kwargs:
                        SimpleNamespace(stdout=str(tmp_path) + '\n' + 'f' * 40 + '\n'))
    observed = reproduction.execution_provenance()
    assert observed.git_revision is None and observed.working_tree_dirty is None


@pytest.mark.parametrize('change,component,index', [
    ('config', 'scenario.config_hash', None),
    ('intervention', 'operation.state_hash', 1),
    ('event', 'events[0].hash', None),
    ('event_output', 'event_hash', None),
    ('state', 'state_hash', None),
    ('ancestry', 'ancestry.checkpoint_id', 0),
])
def test_named_first_divergence(client, manifest, change, component, index):
    data = reproduction.runtime_reproduction(manifest).model_dump(mode='json')
    value = data['manifest']
    if change == 'config': value['scenario']['config']['seed'] += 1
    elif change == 'intervention': value['operations'][1]['command']['value'] = 0
    elif change == 'event': value['event_hashes'][0] = '0' * 64
    elif change == 'event_output': value['event_hash'] = '0' * 64
    elif change == 'state': value['state_hash'] = '0' * 64
    else: value['ancestry'][0]['checkpoint_id'] = 'checkpoint-' + '0' * 64
    response = client.post('/api/sandbox/verify', headers=HEADERS, json=data)
    assert response.status_code == 200
    result = response.json()
    assert not result['verified'] and result['component'] == component
    assert result['operation_index'] == index


@pytest.mark.parametrize('change', ['archive_version', 'engine', 'schema', 'rng', 'missing', 'unknown', 'provenance', 'revision'])
def test_reproduction_rejects_invalid_versions_or_fields(client, manifest, change):
    data = reproduction.runtime_reproduction(manifest).model_dump(mode='json')
    if change == 'archive_version': data['archive_version'] = 'runtime-reproduction/2'
    elif change == 'engine': data['manifest']['engine_version'] = 'future/2'
    elif change == 'schema': data['manifest']['schema_version'] = 'future/2'
    elif change == 'rng': data['manifest']['rng_algorithm'] = 'future/2'
    elif change == 'missing': del data['manifest']['event_hash']
    elif change == 'unknown': data['manifest']['execute'] = 'untrusted-policy'
    elif change == 'provenance': data['provenance']['provenance_version'] = 'future/2'
    else: data['provenance']['git_revision'] = 'not-a-commit'
    assert client.post('/api/sandbox/verify', headers=HEADERS, json=data).status_code == 422
    with pytest.raises(ValidationError): reproduction.read_runtime(canonical(data).encode())


@pytest.mark.parametrize('cli,limit', [('verify_manifest', 2_000_000), ('verify_experiment', 20_000_000)])
@pytest.mark.parametrize('invalid', ['oversized', 'malformed', 'duplicate', 'deep', 'nonfinite'])
def test_independent_cli_rejects_unsafe_json(tmp_path, cli, limit, invalid):
    data = {'oversized': b' ' * (limit + 1), 'malformed': b'{',
            'duplicate': b'{"archive_version":1,"archive_version":2}',
            'deep': b'[' * 2000 + b'0' + b']' * 2000,
            'nonfinite': b'{"manifest":NaN}'}[invalid]
    path = tmp_path / 'invalid.json'; path.write_bytes(data)
    result = subprocess.run([sys.executable, '-m', 'app.sandbox.' + cli, str(path)], capture_output=True, text=True)
    assert result.returncode == 1 and not result.stderr
    assert json.loads(result.stdout)['component'] == 'schema_or_version'


def test_forkcast_export_independent_cli_and_ownership(client, database, tmp_path):
    root = runtime()
    checkpoint = storage.mutate('alice', root.session_id, Command(operation_id='save', expected_revision=0, kind='checkpoint'))
    request = control.ExperimentRequest(operation_id='experiment', checkpoint_id=checkpoint.checkpoint_id,
        expected_revision=1, trials=1, horizon=60, variation=[control.Change(team_id='home', field='tempo', value=100)])
    experiment = control.create_experiment('alice', request)
    for _ in range(30):
        control.tick_experiment('alice', experiment.experiment_id)
        if control.read('experiments', 'alice', experiment.experiment_id)[1].status == 'completed': break
    route = f'/api/sandbox/experiments/{experiment.experiment_id}/reproduction'
    response = client.get(route, headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.headers['Cache-Control'] == 'no-store'
    assert client.get(route).status_code == 403
    assert client.get(route, headers=BOB).status_code == 404
    assert client.post('/api/sandbox/experiments/verify', headers=HEADERS, json=response.json()).json()['verified']
    path = tmp_path / 'forkcast.json'; path.write_text(response.text, encoding='utf-8')
    result = subprocess.run([sys.executable, '-m', 'app.sandbox.verify_experiment', str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert verify_bundle(reproduction.read_forkcast(path.read_bytes())).verified
    data = response.json(); data['manifest']['comparison_hash'] = '0' * 64
    failed = client.post('/api/sandbox/experiments/verify', headers=HEADERS, json=data).json()
    assert not failed['verified'] and failed['component'] == 'comparison_hash'
    assert client.post('/api/sandbox/verify', headers=HEADERS, json=data).status_code == 422


def test_openapi_response_and_auth_contracts(client):
    from app.sandbox.api import router, require_operator
    schema = client.get('/openapi.json').json()
    paths = [('/api/sandbox/checkpoints/{checkpoint_id}', 'get'),
             ('/api/sandbox/sessions/{session_id}/commands', 'post'),
             ('/api/sandbox/sessions/{session_id}/reproduction', 'get'),
             ('/api/sandbox/experiments/{experiment_id}/reproduction', 'get')]
    for path, method in paths:
        assert '200' in schema['paths'][path][method]['responses']
        route = next(r for r in router.routes if getattr(r, 'path', None) == path and method.upper() in r.methods)
        assert any(d.call is require_operator for d in route.dependant.dependencies)
    fields = schema['components']['schemas']['StoredCheckpoint']['properties']
    assert fields['created_at_utc']['anyOf'][1]['type'] == 'null'


@pytest.mark.parametrize('payload,status', [(b' ' * 2_000_001, 413), (b'{', 422),
    (b'{"manifest":1,"manifest":2}', 400), (b'{"manifest":NaN}', 400),
    (b'[' * 40 + b'0' + b']' * 40, 400)], ids=['oversized', 'malformed', 'duplicate', 'nonfinite', 'deep'])
def test_http_verification_rejects_unsafe_input(client, payload, status):
    for path in ['/api/sandbox/verify', '/api/sandbox/experiments/verify']:
        response = client.post(path, headers={**HEADERS, 'Content-Type': 'application/json'}, content=payload)
        assert response.status_code == status, response.text
