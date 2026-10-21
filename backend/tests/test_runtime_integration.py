import json
import sqlite3
import subprocess
import sys
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.sandbox import storage, control
from app.sandbox.control import Change, ExperimentRequest, RunRequest
from app.sandbox.engine import EngineError, build_scenario, canonical, digest, initial_state, apply_command
from app.sandbox.experiments import ExperimentBundle, bundle, comparison, verify_bundle
from app.sandbox.manifest import verify_manifest
from app.sandbox.models import Command, ScenarioConfig

TOKEN = 'runtime-alice-token-32-characters-long'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'data.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(tmp_path / 'runtime.sqlite'))
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '0')
    monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice': TOKEN, 'bob': 'bob-runtime-token-32-characters-long'}))
    return tmp_path


def runtime(duration=600, create='create'):
    scenario = storage.save_scenario('alice', build_scenario(ScenarioConfig(duration_seconds=duration)))
    return storage.create_session('alice', create, scenario.scenario_id)


def command(view, kind='step', **kwargs):
    return storage.mutate('alice', view.session_id, Command(operation_id=f'op-{view.revision}',
        expected_revision=view.revision, kind=kind, **kwargs))


def checkpoint():
    root = command(runtime(), ticks=40)
    return command(root, 'checkpoint')


def experiment_request(root, trials=2, change=True, operation='experiment'):
    return ExperimentRequest(operation_id=operation, checkpoint_id=root.checkpoint_id,
        expected_revision=root.revision, trials=trials, horizon=120,
        variation=[Change(team_id='home', field='pressing', value=100)] if change else [])


def finish_experiment(experiment):
    for _ in range(150):
        control.tick_experiment('alice', experiment.experiment_id)
        experiment = control.read('experiments', 'alice', experiment.experiment_id)[1]
        if experiment.status not in ('queued', 'running'):
            assert experiment.status == 'completed', experiment
            return experiment
    pytest.fail('experiment did not terminate within its bounded plan')


def test_server_run_clock_stop_and_manifest():
    root = runtime(duration=120)
    run = control.create_run('alice', root.session_id, RunRequest(operation_id='run', expected_revision=0, target_tick=100, ticks_per_step=30))
    for _ in range(8):
        control.tick_run('alice', run.run_id)
    run = control.read('runs', 'alice', run.run_id)[1]
    view = storage.get_runtime('alice', root.session_id)
    assert run.status == 'completed' and view.tick == 100 and view.state.lifecycle == 'paused'
    assert verify_manifest(storage.manifest('alice', root.session_id)).verified
    with pytest.raises(EngineError, match='idempotency_conflict'):
        control.create_run('alice', root.session_id, RunRequest(operation_id='run', expected_revision=0, target_tick=90))


def test_crash_after_engine_commit_does_not_double_tick(monkeypatch):
    root = runtime()
    run = control.create_run('alice', root.session_id, RunRequest(operation_id='run', expected_revision=0, target_tick=60, ticks_per_step=20))
    control.tick_run('alice', run.run_id)  # resume
    original = control.save
    monkeypatch.setattr(control, 'save', lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError('interrupted progress commit')))
    with pytest.raises(sqlite3.OperationalError):
        control.tick_run('alice', run.run_id)
    assert storage.get_runtime('alice', root.session_id).tick == 20
    monkeypatch.setattr(control, 'save', original)
    control.tick_run('alice', run.run_id)
    assert storage.get_runtime('alice', root.session_id).tick == 20
    assert control.read('runs', 'alice', run.run_id)[1].step_index == 1


def test_cancel_and_manual_pause_freeze_running_jobs():
    root = runtime()
    run = control.create_run('alice', root.session_id, RunRequest(operation_id='run', expected_revision=0, target_tick=600))
    control.tick_run('alice', run.run_id)
    control.tick_run('alice', run.run_id)
    stopped = control.cancel_run('alice', run.run_id)
    for _ in range(5): control.tick_run('alice', run.run_id)
    assert storage.get_runtime('alice', root.session_id).tick == stopped.tick == 5
    assert storage.get_runtime('alice', root.session_id).state.lifecycle == 'paused'
    request = RunRequest(operation_id='resume', expected_revision=stopped.revision, target_tick=600)
    run = control.create_run('alice', root.session_id, request)
    control.tick_run('alice', run.run_id)
    view = storage.get_runtime('alice', root.session_id)
    command(view, 'pause')
    control.tick_run('alice', run.run_id)
    assert control.read('runs', 'alice', run.run_id)[1].status == 'paused'


def test_parallel_workers_and_fair_bounded_scheduling():
    runs = [control.create_run('alice', runtime(create=f'root-{i}').session_id,
        RunRequest(operation_id=f'run-{i}', expected_revision=0, target_tick=20, ticks_per_step=10)) for i in range(6)]
    control.drive_once(); control.drive_once()
    assert all(control.read('runs', 'alice', r.run_id)[1].status == 'running' for r in runs)
    barrier = Barrier(4)
    def worker(_):
        barrier.wait(timeout=10)
        for _ in range(5): control.drive_once()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(worker, range(4)))
    for r in runs:
        result = control.read('runs', 'alice', r.run_id)[1]
        assert result.status == 'completed' and result.tick == 20
        assert verify_manifest(storage.manifest('alice', r.session_id)).verified


def test_driver_recovery_in_separate_process():
    root = runtime()
    run = control.create_run('alice', root.session_id, RunRequest(operation_id='run', expected_revision=0, target_tick=10, ticks_per_step=10))
    result = subprocess.run([sys.executable, '-c', 'from app.sandbox.control import drive_once; drive_once(); drive_once()'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert control.read('runs', 'alice', run.run_id)[1].status == 'completed'
    assert storage.get_runtime('alice', root.session_id).tick == 10


@pytest.mark.parametrize('change', [False, True])
def test_real_paired_trials_comparison_and_parent_isolation(change):
    root = checkpoint()
    experiment = finish_experiment(control.create_experiment('alice', experiment_request(root, change=change)))
    result = bundle('alice', experiment.experiment_id)
    assert verify_bundle(result).verified
    table = comparison('alice', experiment.experiment_id)
    assert table.verification_status == 'verified_rule_based'
    assert len(table.metrics) == 18 and len(table.trials) == 2
    assert storage.get_runtime('alice', root.session_id).state_hash == root.state_hash
    assert len(set(experiment.branches)) == 4
    for trial in table.trials:
        a = storage.get_runtime('alice', trial.baseline_session_id).state
        b = storage.get_runtime('alice', trial.variation_session_id).state
        assert a.events[:root.event_cursor] == b.events[:root.event_cursor]
        if not change:
            assert digest(a) == digest(b)
        assert trial.rng_counter_offset == trial.trial * 4096
    pressures = next(m for m in table.metrics if m.team_id == 'home' and m.metric == 'pressures')
    actual = [sum(e.type == 'pressure' and e.team_id == 'home' for e in storage.get_runtime('alice', t.variation_session_id).state.events[root.event_cursor:]) for t in table.trials]
    assert pressures.variation.mean == sum(actual) / 2


def test_experiment_boundary_stays_immutable_after_branch_progression():
    experiment = finish_experiment(control.create_experiment('alice', experiment_request(checkpoint(), trials=1)))
    before = bundle('alice', experiment.experiment_id)
    view = storage.get_runtime('alice', experiment.branches[0])
    command(view, ticks=100)
    assert bundle('alice', experiment.experiment_id) == before


def test_paired_rerun_outputs_match():
    root = checkpoint()
    a = finish_experiment(control.create_experiment('alice', experiment_request(root, operation='a')))
    b = finish_experiment(control.create_experiment('alice', experiment_request(root, operation='b')))
    one, two = comparison('alice', a.experiment_id), comparison('alice', b.experiment_id)
    assert [(t.baseline_event_hash, t.variation_event_hash) for t in one.trials] == [(t.baseline_event_hash, t.variation_event_hash) for t in two.trials]
    assert [(m.baseline, m.variation, m.difference) for m in one.metrics] == [(m.baseline, m.variation, m.difference) for m in two.metrics]


@pytest.mark.parametrize('component', ['comparison', 'horizon', 'parent', 'arm'])
def test_bundle_tampering_rejected(component):
    experiment = finish_experiment(control.create_experiment('alice', experiment_request(checkpoint(), trials=1)))
    value = bundle('alice', experiment.experiment_id).model_dump(mode='json')
    if component == 'comparison': value['comparison_hash'] = '0' * 64
    elif component == 'horizon': value['experiment']['request']['horizon'] += 1
    elif component == 'parent': value['parent']['state']['rng']['actor']['counter'] += 1
    else: value['branches'].reverse()
    result = verify_bundle(ExperimentBundle.model_validate(value))
    assert not result.verified and result.component


def test_cancel_experiment_and_owner_checks():
    experiment = control.create_experiment('alice', experiment_request(checkpoint()))
    for _ in range(3): control.tick_experiment('alice', experiment.experiment_id)
    result = control.cancel_experiment('alice', experiment.experiment_id)
    before = [storage.get_runtime('alice', sid).state_hash for sid in result.branches]
    for _ in range(20): control.tick_experiment('alice', experiment.experiment_id)
    assert control.read('experiments', 'alice', experiment.experiment_id)[1].status == 'cancelled'
    assert [storage.get_runtime('alice', sid).state_hash for sid in result.branches] == before
    with pytest.raises(EngineError, match='not_found'):
        control.read('experiments', 'bob', experiment.experiment_id)
    with pytest.raises(EngineError, match='experiment_not_completed'):
        comparison('alice', experiment.experiment_id)


def test_bundle_cli_and_historical_seek(database):
    root = checkpoint()
    source = command(root, ticks=300)
    historical = storage.history_at('alice', root.session_id, 75)
    assert historical['snapshot'].state.tick == 75
    assert all(e.tick <= 75 for e in historical['snapshot'].state.events)
    assert storage.get_runtime('alice', root.session_id).state_hash == source.state_hash
    experiment = finish_experiment(control.create_experiment('alice', experiment_request(root, trials=1)))
    path = database / 'experiment.json'
    path.write_text(canonical(bundle('alice', experiment.experiment_id)), encoding='utf-8')
    process = subprocess.run([sys.executable, '-m', 'app.sandbox.verify_experiment', str(path)], capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)['verified']


def test_websocket_snapshot_delta_reconnect_authorization_and_revocation(monkeypatch):
    root = runtime()
    with TestClient(app) as client:
        path = f'/api/sandbox/sessions/{root.session_id}/observe'
        with client.websocket_connect(path) as socket:
            socket.send_json({'token': TOKEN})
            message = socket.receive_json()
            assert message['kind'] == 'snapshot' and message['view']['tick'] == 0
            response = client.post(f'/api/sandbox/sessions/{root.session_id}/commands', headers=HEADERS,
                json={'operation_id': 'ws-step', 'expected_revision': 0, 'kind': 'step', 'ticks': 30})
            assert response.status_code == 200
            message = socket.receive_json()
            assert message['kind'] == 'delta' and message['from_cursor'] == 1
            assert message['view']['tick'] == 30 and message['events'][0]['sequence'] == 2
            monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice': 'replacement-token-32-characters-long'}))
            socket.send_text('ping')
            with pytest.raises(WebSocketDisconnect): socket.receive_json()
        monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice': TOKEN}))
        with client.websocket_connect(path + '?cursor=1') as socket:
            socket.send_json({'token': TOKEN})
            assert socket.receive_json()['view']['revision'] == 1
        with client.websocket_connect(path) as socket:
            socket.send_json({'token': 'wrong'})
            with pytest.raises(WebSocketDisconnect) as error: socket.receive_json()
            assert error.value.code == 4403
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(path, headers={'Origin': 'https://untrusted.example'}): pass


def test_lifespan_driver_progresses_without_browser_clock(monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_DRIVER', '1')
    root = runtime(duration=120)
    with TestClient(app) as client:
        response = client.post(f'/api/sandbox/sessions/{root.session_id}/runs', headers=HEADERS,
            json={'operation_id': 'live', 'expected_revision': 0, 'target_tick': 120, 'ticks_per_step': 60})
        assert response.status_code == 200, response.text
        identity = response.json()['run_id']
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            run = control.read('runs', 'alice', identity)[1]
            if run.status == 'completed': break
            time.sleep(.05)
        assert run.status == 'completed' and run.tick == 120
        assert storage.get_runtime('alice', root.session_id).state.lifecycle == 'completed'


def test_runtime_schema_one_upgrade_preserves_receipts(database):
    root = command(runtime(), ticks=10)
    with storage.connect() as db:
        db.execute('DROP TABLE runs'); db.execute('DROP TABLE experiments'); db.execute('PRAGMA user_version=1')
    assert storage.get_runtime('alice', root.session_id).state_hash == root.state_hash
    with storage.connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
    repeated = storage.mutate('alice', root.session_id, Command(operation_id='op-0', expected_revision=0, kind='step', ticks=10))
    assert repeated == root


def test_parallel_experiment_workers_and_zero_results():
    root = command(runtime(), 'checkpoint')
    experiment = control.create_experiment('alice', ExperimentRequest(operation_id='zero', checkpoint_id=root.checkpoint_id,
        expected_revision=root.revision, trials=2, horizon=1))
    barrier = Barrier(3)
    def worker(_):
        barrier.wait(timeout=10)
        for _ in range(40): control.tick_experiment('alice', experiment.experiment_id)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(worker, range(3)))
    result = comparison('alice', experiment.experiment_id)
    assert len(control.read('experiments', 'alice', experiment.experiment_id)[1].branches) == 4
    for row in result.metrics:
        if row.metric == 'goals':
            assert row.baseline.mean == row.variation.mean == row.difference == 0
            assert row.evidence_count == 0 and not row.evidence


def test_control_migration_interruption_is_atomic(monkeypatch):
    root = command(runtime(), ticks=10)
    path = storage.runtime_database_path()
    with storage.connect() as db:
        db.execute('DROP TABLE runs'); db.execute('DROP TABLE experiments'); db.execute('PRAGMA user_version=1')
    original = storage.CONTROL_DDL
    monkeypatch.setattr(storage, 'CONTROL_DDL', original[:1] + ('INVALID SQL',))
    with pytest.raises(sqlite3.OperationalError):
        storage.get_runtime('alice', root.session_id)
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 1
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='runs'").fetchone()
        assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1
    monkeypatch.setattr(storage, 'CONTROL_DDL', original)
    assert storage.get_runtime('alice', root.session_id).state_hash == root.state_hash


def test_schema_two_backup_preserves_active_jobs(database, monkeypatch):
    from app.sandbox.backup import copy_database
    root = runtime()
    run = control.create_run('alice', root.session_id, RunRequest(operation_id='run', expected_revision=0, target_tick=50, ticks_per_step=25))
    control.tick_run('alice', run.run_id)
    target = database / 'backup.sqlite'
    result = copy_database(storage.runtime_database_path(), target)
    assert result['schema_version'] == 2
    recovered = database / 'recovered.sqlite'
    copy_database(target, recovered, result['sha256'])
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(recovered))
    for _ in range(3): control.tick_run('alice', run.run_id)
    assert control.read('runs', 'alice', run.run_id)[1].status == 'completed'
    assert storage.get_runtime('alice', root.session_id).tick == 50


def test_committed_forkcast_bundle_verifies_without_database():
    path = Path(__file__).resolve().parents[2] / 'docs' / 'examples' / 'sandbox' / 'forkcast.json'
    result = verify_bundle(ExperimentBundle.model_validate_json(path.read_bytes()))
    assert result.verified, result


def test_long_slow_runs_reject_insufficient_command_budget_without_partial_state():
    root = runtime(duration=5400)
    with pytest.raises(EngineError, match='run_exceeds_command_budget'):
        control.create_run('alice', root.session_id, RunRequest(operation_id='too-slow', expected_revision=0, target_tick=5400, ticks_per_step=1))
    assert storage.get_runtime('alice', root.session_id).state_hash == root.state_hash
    assert not control.list_runs('alice', root.session_id)
    # A suitable bounded rate is accepted for the same full match.
    assert control.create_run('alice', root.session_id, RunRequest(operation_id='bounded', expected_revision=0, target_tick=5400, ticks_per_step=5)).status == 'queued'
