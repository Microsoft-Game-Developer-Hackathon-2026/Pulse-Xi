"""Calendar metadata is atomic, owner-private, and absent from replay inputs."""
import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sandbox import storage, control
from app.sandbox.backup import copy_database
from app.sandbox.engine import canonical
from app.sandbox.experiments import bundle, verify_bundle
from app.sandbox.manifest import verify_manifest
from app.sandbox.models import Command
from test_authoritative_engine import database, runtime


FIRST = '2026-10-21T18:00:00.000001Z'
SECOND = '2026-10-22T18:00:00.000002Z'
TOKEN = 'checkpoint-alice-token-at-least-32-characters'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}
BOB = {'Authorization': 'Bearer bob-checkpoint-token-at-least-32-characters'}


def checkpoint():
    root = runtime()
    command = Command(operation_id='save', expected_revision=0, kind='checkpoint')
    return root, command


@pytest.fixture
def client(database, monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice': TOKEN, 'bob': BOB['Authorization'][7:]}))
    return TestClient(app)


def test_receipt_retry_lost_response_and_owner_private_metadata(client, monkeypatch):
    root, command = checkpoint()
    route = f'/api/sandbox/sessions/{root.session_id}/commands'
    monkeypatch.setattr(storage, 'utc_now', lambda: FIRST)
    # Commit succeeds even if the caller loses the first response.
    first = storage.mutate('alice', root.session_id, command)
    storage.mutate('alice', root.session_id, Command(operation_id='later', expected_revision=1, kind='step', ticks=10))
    monkeypatch.setattr(storage, 'utc_now', lambda: SECOND)
    retry = client.post(route, headers=HEADERS, json=command.model_dump(mode='json'))
    assert retry.status_code == 200
    assert retry.json()['checkpoint_created_at_utc'] == FIRST
    assert retry.json()['state_hash'] == first.state_hash
    assert retry.json() == client.post(route, headers=HEADERS, json=command.model_dump(mode='json')).json()
    path = f'/api/sandbox/checkpoints/{first.checkpoint_id}'
    saved = client.get(path, headers=HEADERS).json()
    assert saved['created_at_utc'] == FIRST
    assert 'created_at_utc' not in canonical(saved['snapshot'])
    assert client.get(path).status_code == 403
    assert client.get(path, headers=BOB).status_code == 404
    assert client.get(f'/api/sandbox/sessions/{root.session_id}/checkpoints', headers=BOB).status_code == 404
    assert client.get(f'/api/sandbox/sessions/{root.session_id}/checkpoints', headers=HEADERS).json()[0]['created_at_utc'] == FIRST
    assert client.post(route, headers=BOB, json=command.model_dump(mode='json')).status_code == 404


def test_concurrent_checkpoint_retries_record_creation_once(database, monkeypatch):
    root, command = checkpoint()
    calls = []
    def clock():
        calls.append(1)
        return FIRST
    monkeypatch.setattr(storage, 'utc_now', clock)
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(lambda _: storage.mutate('alice', root.session_id, command), range(4)))
    assert len(calls) == 1
    assert all(r == receipts[0] for r in receipts)
    with storage.connect() as db:
        assert db.execute('SELECT * FROM checkpoint_metadata').fetchall() == [(receipts[0].checkpoint_id, FIRST)]
        assert db.execute('SELECT COUNT(*) FROM commands').fetchone()[0] == 1


def test_http_failure_after_checkpoint_commit_recovers_original_metadata(client, monkeypatch):
    root, command = checkpoint()
    monkeypatch.setattr(storage, 'utc_now', lambda: FIRST)
    original = storage.get_checkpoint
    def interrupted(*args):
        raise storage.EngineError('interrupted_response', 503)
    monkeypatch.setattr(storage, 'get_checkpoint', interrupted)
    route = f'/api/sandbox/sessions/{root.session_id}/commands'
    first = client.post(route, headers=HEADERS, json=command.model_dump(mode='json'))
    assert first.status_code == 503
    assert storage.get_runtime('alice', root.session_id).revision == 1
    monkeypatch.setattr(storage, 'get_checkpoint', original)
    monkeypatch.setattr(storage, 'utc_now', lambda: SECOND)
    recovered = client.post(route, headers=HEADERS, json=command.model_dump(mode='json'))
    assert recovered.status_code == 200
    assert recovered.json()['checkpoint_created_at_utc'] == FIRST
    assert storage.get_runtime('alice', root.session_id).revision == 1


def test_checkpoint_metadata_write_failure_rolls_back_everything(client):
    root, command = checkpoint()
    with storage.connect() as db:
        before = {table: db.execute(f'SELECT * FROM {table}').fetchall() for table in
                  ('sessions', 'commands', 'checkpoints', 'runtime_events', 'audit', 'checkpoint_metadata')}
        db.execute("CREATE TRIGGER injected_checkpoint_failure BEFORE INSERT ON checkpoint_metadata BEGIN SELECT RAISE(ABORT, 'injected'); END")
    response = client.post(f'/api/sandbox/sessions/{root.session_id}/commands', headers=HEADERS, json=command.model_dump(mode='json'))
    assert response.status_code == 503 and response.json()['detail']['code'] == 'transaction_failed'
    with storage.connect() as db:
        for table, rows in before.items():
            assert db.execute(f'SELECT * FROM {table}').fetchall() == rows
        db.execute('DROP TRIGGER injected_checkpoint_failure')
    assert storage.mutate('alice', root.session_id, command).revision == 1


@pytest.mark.parametrize('version', [1, 2, 3])
def test_historical_migration_backup_and_reopen_preserve_records(database, monkeypatch, version):
    root, command = checkpoint()
    saved = storage.mutate('alice', root.session_id, command)
    run = control.create_run('alice', root.session_id, control.RunRequest(operation_id='run', expected_revision=1, target_tick=20))
    experiment = control.create_experiment('alice', control.ExperimentRequest(operation_id='experiment', checkpoint_id=saved.checkpoint_id, expected_revision=1, horizon=20))
    path = storage.runtime_database_path()
    with sqlite3.connect(path) as db:
        tables = ['scenarios', 'sessions', 'commands', 'checkpoints', 'runtime_events', 'audit']
        if version >= 2: tables += ['runs', 'experiments']
        if version >= 3: tables += ['scenario_metadata']
        before = {table: db.execute(f'SELECT * FROM {table}').fetchall() for table in tables}
        db.execute('DROP TABLE checkpoint_metadata')
        if version < 3: db.execute('DROP TABLE scenario_metadata')
        if version < 2:
            db.execute('DROP TABLE runs'); db.execute('DROP TABLE experiments')
        db.execute(f'PRAGMA user_version={version}')
    # Offline backup must continue to accept every supported historical schema.
    backup = database / f'legacy-{version}.sqlite'
    assert copy_database(path, backup)['schema_version'] == version
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(backup))
    migrated = storage.get_checkpoint('alice', saved.checkpoint_id)
    assert migrated.created_at_utc is None
    assert migrated.snapshot.state_hash == saved.state_hash
    with storage.connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 4
        for table, rows in before.items():
            assert db.execute(f'SELECT * FROM {table}').fetchall() == rows
    if version >= 2:
        assert control.read('runs', 'alice', run.run_id)[1] == run
        assert control.read('experiments', 'alice', experiment.experiment_id)[1] == experiment
    assert storage.mutate('alice', root.session_id, command) == saved
    assert storage.get_checkpoint('alice', saved.checkpoint_id).created_at_utc is None


def test_checkpoint_migration_failure_is_atomic(database, monkeypatch):
    root, command = checkpoint()
    saved = storage.mutate('alice', root.session_id, command)
    with sqlite3.connect(storage.runtime_database_path()) as db:
        db.execute('DROP TABLE checkpoint_metadata'); db.execute('PRAGMA user_version=3')
        before = db.execute('SELECT * FROM checkpoints').fetchall()
    original = storage.CHECKPOINT_METADATA_DDL
    monkeypatch.setattr(storage, 'CHECKPOINT_METADATA_DDL', original[:1] + ('INVALID SQL',))
    with pytest.raises(sqlite3.OperationalError): storage.get_checkpoint('alice', saved.checkpoint_id)
    with sqlite3.connect(storage.runtime_database_path()) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 3
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='checkpoint_metadata'").fetchone()
        assert db.execute('SELECT * FROM checkpoints').fetchall() == before
    monkeypatch.setattr(storage, 'CHECKPOINT_METADATA_DDL', original)
    assert storage.get_checkpoint('alice', saved.checkpoint_id).created_at_utc is None


def test_backup_restore_keeps_original_timestamp_and_hashes(database, monkeypatch):
    root, command = checkpoint()
    monkeypatch.setattr(storage, 'utc_now', lambda: FIRST)
    saved = storage.mutate('alice', root.session_id, command)
    original = storage.get_checkpoint('alice', saved.checkpoint_id)
    backup = database / 'backup.sqlite'
    result = copy_database(storage.runtime_database_path(), backup)
    recovered = database / 'recovered.sqlite'
    copy_database(backup, recovered, result['sha256'])
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(recovered))
    assert storage.get_checkpoint('alice', saved.checkpoint_id) == original
    assert storage.mutate('alice', root.session_id, command) == saved
    program = '''
import sys
from app.sandbox import storage
from app.sandbox.engine import canonical
from app.sandbox.models import Command
receipt = storage.mutate('alice', sys.argv[1], Command.model_validate_json(sys.argv[2]))
print(canonical(storage.get_checkpoint('alice', receipt.checkpoint_id)))
'''
    process = subprocess.run([sys.executable, '-c', program, root.session_id, canonical(command)], capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == original.model_dump(mode='json')


def test_calendar_metadata_does_not_change_continuation_or_experiment_hashes(database, monkeypatch):
    outputs = []
    for index, timestamp in enumerate([FIRST, SECOND]):
        monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(database / f'run-{index}.sqlite'))
        monkeypatch.setattr(storage, 'utc_now', lambda: timestamp)
        root, command = checkpoint()
        saved = storage.mutate('alice', root.session_id, command)
        source = storage.get_checkpoint('alice', saved.checkpoint_id)
        child = storage.create_session('alice', 'fork', checkpoint_id=saved.checkpoint_id, expected_revision=saved.revision)
        changed = storage.mutate('alice', child.session_id, Command(operation_id='press', expected_revision=1, kind='intervene',
            requested_tick=0, team_id='home', field='pressing', value=100))
        storage.mutate('alice', child.session_id, Command(operation_id='play', expected_revision=changed.revision, kind='step', ticks=120))
        manifest = storage.manifest('alice', child.session_id)
        assert verify_manifest(manifest).verified
        exp = control.create_experiment('alice', control.ExperimentRequest(operation_id='experiment', checkpoint_id=saved.checkpoint_id,
            expected_revision=1, trials=1, horizon=60, variation=[control.Change(team_id='home', field='pressing', value=100)]))
        for _ in range(20):
            control.tick_experiment('alice', exp.experiment_id)
            if control.read('experiments', 'alice', exp.experiment_id)[1].status == 'completed': break
        result = bundle('alice', exp.experiment_id)
        assert verify_bundle(result).verified
        assert storage.get_runtime('alice', root.session_id).state_hash == saved.state_hash
        assert source.created_at_utc == timestamp
        outputs.append((canonical(source.snapshot), canonical(manifest), canonical(result)))
    assert outputs[0] == outputs[1]
