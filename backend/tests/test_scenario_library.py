"""Scenario archives exercise real HTTP, migrations and engine continuation."""
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sandbox import storage, control
from app.sandbox.backup import copy_database
from app.sandbox.engine import EngineError, build_scenario, canonical, digest, initial_state, presets, draw
from app.sandbox.models import Command, ScenarioConfig, STREAMS, ENGINE_VERSION
from app.sandbox.scenario_archive import ScenarioArchive
from test_authoritative_engine import database, until

TOKEN = 'scenario-alice-token-at-least-32-characters'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}
BOB = {'Authorization': 'Bearer bob-scenario-token-at-least-32-characters'}


@pytest.fixture
def client(database, monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice': TOKEN, 'bob': BOB['Authorization'][7:]}))
    return TestClient(app)


def create(client, config=None, headers=HEADERS):
    response = client.post('/api/sandbox/scenarios', headers=headers, json=config or {'duration_seconds': 120})
    assert response.status_code == 200, response.text
    return response.json()


def archive(client, scenario, headers=HEADERS):
    response = client.get(f"/api/sandbox/scenarios/{scenario['scenario_id']}/archive", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_owner_scoped_list_read_and_stable_order(client):
    empty = client.get('/api/sandbox/scenarios', headers=HEADERS)
    assert empty.json() == [] and empty.headers['Cache-Control'] == 'no-store'
    first = create(client)
    second = create(client, {'seed': 8})
    create(client, {'seed': 9}, BOB)
    rows = client.get('/api/sandbox/scenarios', headers=HEADERS).json()
    assert [r['scenario_id'] for r in rows] == sorted([first['scenario_id'], second['scenario_id']])
    assert all(r['created_at_utc'].endswith('Z') for r in rows)
    assert len(client.get('/api/sandbox/scenarios', headers=BOB).json()) == 1
    for path in ('/scenarios', f"/scenarios/{first['scenario_id']}", f"/scenarios/{first['scenario_id']}/archive"):
        assert client.get('/api/sandbox' + path).status_code == 403
    assert client.get(f"/api/sandbox/scenarios/{first['scenario_id']}/archive", headers=BOB).status_code == 404
    # Identical content may be saved by two owners, without exposing ownership.
    assert create(client, first['config'], BOB) == first
    assert len(client.get('/api/sandbox/scenarios', headers=BOB).json()) == 2
    assert TOKEN not in canonical(rows)
    assert client.get(f"/api/sandbox/scenarios/{first['scenario_id']}/archive", headers=HEADERS).headers['Cache-Control'] == 'no-store'


@pytest.mark.parametrize('name', list(presets()))
def test_presets_canonicalization_hash_and_event_reproduction(name):
    config = presets()[name]
    scenario = build_scenario(config)
    text = json.dumps(config.model_dump(mode='json'), sort_keys=True, indent=4)
    reordered = dict(reversed(list(json.loads(text).items())))
    assert build_scenario(ScenarioConfig.model_validate(reordered)) == scenario
    first = until(initial_state(scenario), 5400)
    second = until(initial_state(build_scenario(ScenarioConfig.model_validate_json(text))), 5400)
    assert digest(first.events) == digest(second.events)
    changed = config.model_copy(deep=True)
    changed.home.tactics.tempo = (changed.home.tactics.tempo + 1) % 101
    assert build_scenario(changed).config_hash != scenario.config_hash
    assert len({build_scenario(c).config_hash for c in presets().values()}) == 4


def test_rng_stream_derivation_and_draw_isolation():
    state = initial_state(build_scenario(ScenarioConfig(seed=177)))
    before = {name: rng.model_copy() for name, rng in state.rng.items()}
    for name in STREAMS:
        key = hashlib.sha256(f'{ENGINE_VERSION}:177:{name}'.encode()).hexdigest()
        assert state.rng[name].key == key
    value = draw(state, 'actor')
    assert value == int.from_bytes(hashlib.sha256(f"{before['actor'].key}:0".encode()).digest(), 'big') % 100
    assert state.rng['actor'].counter == 1
    assert all(state.rng[name] == before[name] for name in STREAMS if name != 'actor')


def test_export_import_fresh_database_preserves_events_and_provenance(client, database, monkeypatch):
    scenario = create(client)
    exported = archive(client, scenario)
    assert exported['scenario'] == scenario
    assert exported['rng_streams'] == list(STREAMS)
    before = until(initial_state(build_scenario(ScenarioConfig.model_validate(scenario['config']))), 120)
    with storage.connect() as db:
        persisted_payload = db.execute('SELECT payload FROM scenarios').fetchone()[0]
    assert 'created_at_utc' not in persisted_payload
    original = storage.runtime_database_path()
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(database / 'fresh.sqlite'))
    imported = client.post('/api/sandbox/scenarios/import', headers=HEADERS, json=exported)
    assert imported.status_code == 200, imported.text
    assert imported.json() == exported
    restored = storage.get_scenario('alice', scenario['scenario_id'])
    after = until(initial_state(restored), 120)
    assert digest(before) == digest(after) and digest(before.events) == digest(after.events)
    assert archive(client, scenario) == exported  # each storage access reopens SQLite
    newer = {**exported, 'created_at_utc': '2001-01-01T00:00:00Z'}
    assert client.post('/api/sandbox/scenarios/import', headers=HEADERS, json=newer).json() == exported
    assert digest(until(initial_state(restored), 120)) == digest(before)
    assert original != storage.runtime_database_path()


@pytest.mark.parametrize('change', ['hash', 'id', 'config'])
def test_import_identity_tampering_rejected_without_writes(client, change):
    scenario = create(client)
    data = archive(client, scenario)
    if change == 'hash': data['scenario']['config_hash'] = '0' * 64
    if change == 'id': data['scenario']['scenario_id'] = 'scenario-' + '0' * 64
    if change == 'config': data['scenario']['config']['seed'] += 1
    response = client.post('/api/sandbox/scenarios/import', headers=HEADERS, json=data)
    assert response.status_code == 409 and response.json()['detail']['code'] == 'scenario_hash_mismatch'
    assert len(storage.list_scenarios('alice')) == 1


@pytest.mark.parametrize('field,value', [('archive_version', 'scenario-archive/2'), ('rng_algorithm', 'random/1'),
    ('rng_derivation', 'other'), ('rng_streams', ['actor']), ('unknown', True),
    ('created_at_utc', '2026-10-21T10:00:00+01:00'), ('created_at_utc', 'not a date'),
    ('created_at_utc', '2026-10-21\n10:00:00Z')])
def test_invalid_archive_metadata(client, field, value):
    data = archive(client, create(client))
    data[field] = value
    assert client.post('/api/sandbox/scenarios/import', headers=HEADERS, json=data).status_code == 422


@pytest.mark.parametrize('field,value', [('seed', -1), ('seed', 2147483648), ('duration_seconds', 59), ('duration_seconds', 61), ('duration_seconds', 5402), ('environment', 'rain'),
    ('engine_version', 'zone-engine/2'), ('schema_version', 'sandbox/2'), ('unknown', 1)])
def test_invalid_config_versions_and_bounds(client, field, value):
    assert client.post('/api/sandbox/scenarios/import', headers=HEADERS, json={field: value}).status_code == 422


@pytest.mark.parametrize('change', ['formation', 'attribute', 'tactic', 'roster', 'ids'])
def test_invalid_resolved_rosters_and_tactics(client, change):
    config = create(client)['config']
    if change == 'formation': config['away']['tactics']['formation'] = '2-2-6'
    if change == 'attribute': config['home']['players'][0]['passing'] = 101
    if change == 'tactic': config['away']['tactics']['pressing'] = -1
    if change == 'roster': config['away']['players'].pop()
    if change == 'ids': config['away']['players'][0]['player_id'] = config['home']['players'][0]['player_id']
    assert client.post('/api/sandbox/scenarios/import', headers=HEADERS, json=config).status_code == 422


def test_import_request_boundary_and_legacy_contract(client):
    for body, status in [('{', 422), ('{"seed":1,"seed":2}', 400), ('{"seed":NaN}', 400),
                         (' ' * 2_000_001, 413)]:
        response = client.post('/api/sandbox/scenarios/import', headers={**HEADERS, 'Content-Type': 'application/json'}, content=body)
        assert response.status_code == status
    assert client.post('/api/sandbox/scenarios/import', json={}).status_code == 403
    saved = client.post('/api/sandbox/scenarios/import', headers=HEADERS, json={'seed': 81})
    assert saved.status_code == 200
    scenario = saved.json()['scenario']
    assert client.get(f"/api/sandbox/scenarios/{scenario['scenario_id']}", headers=HEADERS).json() == scenario
    assert create(client, {'seed': 81}) == scenario


@pytest.mark.parametrize('credential', ['Bearer wrong', 'Basic wrong', b'Bearer \xff'])
def test_library_credentials_fail_closed(client, credential):
    headers = {'Authorization': credential}
    assert client.get('/api/sandbox/scenarios', headers=headers).status_code == 403
    assert client.get('/api/sandbox/scenarios/unknown/archive', headers=headers).status_code == 403
    assert client.post('/api/sandbox/scenarios/import', headers=headers, json={}).status_code == 403


def test_distinct_archive_timestamps_leave_persisted_engine_hashes_equal(client, database, monkeypatch):
    data = archive(client, create(client))
    hashes = []
    for index, timestamp in enumerate(['2000-01-01T00:00:00Z', '2026-10-21T14:00:00Z', None]):
        monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(database / f'timestamp-{index}.sqlite'))
        imported = client.post('/api/sandbox/scenarios/import', headers=HEADERS, json={**data, 'created_at_utc': timestamp})
        assert imported.status_code == 200 and imported.json()['created_at_utc'] == timestamp
        root = storage.create_session('alice', 'same-operation', data['scenario']['scenario_id'])
        result = storage.mutate('alice', root.session_id, Command(operation_id='finish', expected_revision=0, kind='step', ticks=120))
        hashes.append((result.state_hash, result.event_hash))
    assert len(set(hashes)) == 1


def test_committed_scenario_archive_example_imports(client):
    path = Path(__file__).resolve().parents[2] / 'docs/examples/sandbox/scenario.json'
    sample = ScenarioArchive.model_validate_json(path.read_bytes())
    imported = client.post('/api/sandbox/scenarios/import', headers=HEADERS, json=sample.model_dump(mode='json'))
    assert imported.status_code == 200 and imported.json() == sample.model_dump(mode='json')


def test_archive_to_persisted_fulltime_tactics_analysis_and_manifest(client, database, monkeypatch):
    exported = archive(client, create(client, {'seed': 177, 'duration_seconds': 5400}))
    results = []
    for trial in range(2):
        monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(database / f'integrated-{trial}.sqlite'))
        imported = client.post('/api/sandbox/scenarios/import', headers=HEADERS, json=exported)
        assert imported.status_code == 200
        root = client.post('/api/sandbox/sessions', headers=HEADERS, json={
            'operation_id': 'archive-world', 'scenario_id': exported['scenario']['scenario_id']}).json()
        base = '/api/sandbox/sessions/' + root['session_id']
        changed = client.post(base + '/commands', headers=HEADERS, json={
            'operation_id': 'policy', 'kind': 'intervene', 'expected_revision': 0,
            'requested_tick': 0, 'team_id': 'home', 'field': 'pressing', 'value': 90})
        assert changed.status_code == 200
        revision = changed.json()['revision']
        for step in range(18):
            response = client.post(base + '/commands', headers=HEADERS, json={
                'operation_id': f'step-{step}', 'kind': 'step', 'expected_revision': revision, 'ticks': 300})
            assert response.status_code == 200, response.text
            revision = response.json()['revision']
        view = client.get(base + '/state', headers=HEADERS).json()
        assert view['tick'] == 5400 and view['state']['lifecycle'] == 'completed'
        assert view['state']['tactics']['home']['pressing'] == 90
        assert view['state']['events'][-1]['type'] == 'fulltime'
        analysis = client.get(base + '/analysis?at_second=5400', headers=HEADERS).json()
        for team in ('home', 'away'):
            assert analysis['metrics'][team]['goals'] == view['state']['score'][team]
        manifest = client.get(base + '/manifest', headers=HEADERS).json()
        assert client.post('/api/sandbox/verify', headers=HEADERS, json=manifest).json()['verified']
        assert client.get('/api/matches/' + root['session_id']).status_code == 404
        results.append((view['state_hash'], view['event_hash'], analysis['metrics']))
    assert results[0] == results[1]


def test_conflicting_stored_payload_and_capacity(client):
    first = create(client)
    data = archive(client, first)
    with storage.connect() as db:
        corrupt = {**first, 'config_hash': 'f' * 64}
        db.execute('UPDATE scenarios SET payload=? WHERE owner=? AND id=?', (canonical(corrupt), 'alice', first['scenario_id']))
    assert client.post('/api/sandbox/scenarios/import', headers=HEADERS, json=data).status_code == 409
    with storage.connect() as db:
        db.execute('UPDATE scenarios SET payload=? WHERE owner=? AND id=?', (canonical(first), 'alice', first['scenario_id']))
    for seed in range(99):
        create(client, {'seed': seed, 'duration_seconds': 60})
    rows = client.get('/api/sandbox/scenarios', headers=HEADERS).json()
    assert len(rows) == 100
    assert [r['scenario_id'] for r in rows] == sorted(r['scenario_id'] for r in rows)
    assert client.post('/api/sandbox/scenarios', headers=HEADERS, json={'seed': 999}).status_code == 429
    assert create(client, first['config']) == first  # retry still works at capacity


def test_concurrent_creation_has_one_stable_timestamp(client):
    def save(_):
        scenario = storage.save_scenario('alice', build_scenario(ScenarioConfig()))
        return storage.get_scenario_archive('alice', scenario.scenario_id)
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(save, range(4)))
    assert all(item == result[0] for item in result)
    assert len(storage.list_scenarios('alice')) == 1


@pytest.mark.parametrize('version', [0, 1, 2])
def test_supported_runtime_migrations_preserve_records(client, database, version):
    path = storage.runtime_database_path()
    if version == 0:
        with storage.connect() as db:
            assert db.execute('PRAGMA user_version').fetchone()[0] == 4
        return
    scenario = create(client)
    receipt = storage.create_session('alice', 'migration', scenario['scenario_id'])
    receipt = storage.mutate('alice', receipt.session_id, Command(operation_id='checkpoint', expected_revision=0, kind='checkpoint'))
    run = control.create_run('alice', receipt.session_id, control.RunRequest(operation_id='migration-run', expected_revision=1, target_tick=60))
    experiment = control.create_experiment('alice', control.ExperimentRequest(operation_id='migration-exp', checkpoint_id=receipt.checkpoint_id, expected_revision=1, horizon=30))
    with sqlite3.connect(path) as db:
        before = {t: db.execute(f'SELECT * FROM {t}').fetchall() for t in ('scenarios','sessions','commands','runtime_events','checkpoints','audit','runs','experiments')}
        db.execute('DROP TABLE checkpoint_metadata'); db.execute('DROP TABLE scenario_metadata')
        if version == 1:
            db.execute('DROP TABLE runs'); db.execute('DROP TABLE experiments')
        db.execute(f'PRAGMA user_version={version}')
    assert storage.get_runtime('alice', receipt.session_id).state_hash == receipt.state_hash
    with storage.connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 4
        for table, rows in before.items():
            if version == 1 and table in ('runs', 'experiments'): continue
            assert db.execute(f'SELECT * FROM {table}').fetchall() == rows
    assert storage.get_scenario_archive('alice', scenario['scenario_id']).created_at_utc is None
    if version == 2:
        assert control.read('runs', 'alice', run.run_id)[1] == run
        assert control.read('experiments', 'alice', experiment.experiment_id)[1] == experiment


def test_metadata_migration_failure_rolls_back(client, monkeypatch):
    scenario = create(client)
    path = storage.runtime_database_path()
    with sqlite3.connect(path) as db:
        db.execute('DROP TABLE checkpoint_metadata'); db.execute('DROP TABLE scenario_metadata'); db.execute('PRAGMA user_version=2')
    original = storage.SCENARIO_METADATA_DDL
    monkeypatch.setattr(storage, 'SCENARIO_METADATA_DDL', original[:1] + ('INVALID SQL',))
    with pytest.raises(sqlite3.OperationalError):
        storage.get_scenario('alice', scenario['scenario_id'])
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='scenario_metadata'").fetchone()
        assert db.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0] == 1
    monkeypatch.setattr(storage, 'SCENARIO_METADATA_DDL', original)
    assert storage.get_scenario('alice', scenario['scenario_id']).config_hash == scenario['config_hash']


def test_metadata_write_failure_is_atomic(client):
    with storage.connect() as db:
        db.execute("CREATE TRIGGER injected_metadata_failure BEFORE INSERT ON scenario_metadata BEGIN SELECT RAISE(ABORT, 'injected'); END")
    assert client.post('/api/sandbox/scenarios', headers=HEADERS, json={}).status_code == 503
    with storage.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM scenario_metadata').fetchone()[0] == 0
        db.execute('DROP TRIGGER injected_metadata_failure')
    assert create(client)


def test_new_openapi_contracts_keep_operator_dependencies(client):
    from app.sandbox.api import require_operator, router
    spec = client.get('/openapi.json').json()
    routes = [('/api/sandbox/scenarios', 'get'), ('/api/sandbox/scenarios/import', 'post'),
              ('/api/sandbox/scenarios/{scenario_id}/archive', 'get')]
    for path, method in routes:
        matches = [r for r in router.routes if getattr(r, 'path', None) == path and method.upper() in getattr(r, 'methods', set())]
        assert len(matches) == 1
        assert any(d.call is require_operator for d in matches[0].dependant.dependencies)
        assert '200' in spec['paths'][path][method]['responses']
    union = spec['paths']['/api/sandbox/scenarios/import']['post']['requestBody']['content']['application/json']['schema']['anyOf']
    assert len(union) == 2
    assert all(spec['components']['schemas'][item['$ref'].rsplit('/', 1)[-1]]['additionalProperties'] is False for item in union)
    assert {'400', '413', '422'} <= set(spec['paths']['/api/sandbox/scenarios/import']['post']['responses'])


def test_archive_backup_and_imported_database_separation(client, database, monkeypatch):
    from app.storage import connect as library_connect, ingest_package, imported_snapshot
    from app.simulator import generate
    match, events = generate('comeback')
    match = match.model_copy(update={'match_id': 'preserved-library-dataset'})
    events = [event.model_copy(update={'match_id': match.match_id}) for event in events[:20]]
    ingest_package(match, events, {'source': 'synthetic regression fixture'})
    before = imported_snapshot(match.match_id)
    with library_connect() as db:
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        lifecycle = db.execute('SELECT * FROM match_lifecycle').fetchall()
    scenario = create(client)
    data = archive(client, scenario)
    target = database / 'backup.sqlite'
    result = copy_database(storage.runtime_database_path(), target)
    assert result['schema_version'] == 4
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(target))
    assert archive(client, scenario) == data
    with library_connect() as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == tables
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        assert db.execute('SELECT * FROM match_lifecycle').fetchall() == lifecycle
    assert imported_snapshot(match.match_id) == before


@pytest.mark.parametrize('version', [1, 2])
def test_legacy_runtime_backups_open_and_upgrade(client, database, monkeypatch, version):
    scenario = create(client)
    path = storage.runtime_database_path()
    with sqlite3.connect(path) as db:
        db.execute('DROP TABLE checkpoint_metadata'); db.execute('DROP TABLE scenario_metadata')
        if version == 1:
            db.execute('DROP TABLE runs'); db.execute('DROP TABLE experiments')
        db.execute(f'PRAGMA user_version={version}')
    recovered = database / 'legacy-recovered.sqlite'
    result = copy_database(path, recovered)
    assert result['schema_version'] == version
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(recovered))
    assert storage.get_scenario_archive('alice', scenario['scenario_id']).created_at_utc is None
    with storage.connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 4
