"""Executable conformance tests using real transitions, SQLite and authenticated HTTP."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.sandbox import storage
from app.sandbox.engine import (EngineError, apply_command, build_scenario, canonical, capture_state,
                                digest, initial_state, match_events, match_record, presets, restore_state)
from app.sandbox.manifest import verify_manifest
from app.sandbox.models import Command, ExperimentManifest, ScenarioConfig


def make_state(seed=7, duration=5400):
    return initial_state(build_scenario(ScenarioConfig(seed=seed, duration_seconds=duration)))


def command(state, kind='step', **kwargs):
    return Command(operation_id=f'op-{state.revision}', expected_revision=state.revision, kind=kind, **kwargs)


def until(state, tick):
    while state.tick < tick:
        state = apply_command(state, command(state, ticks=min(300, tick - state.tick)))
    return state


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(tmp_path / 'runtime.sqlite'))
    monkeypatch.setenv('PULSE_DB_PATH', str(tmp_path / 'data.sqlite'))
    return tmp_path


def runtime(owner='alice', seed=7, duration=120, operation_id='create'):
    scenario = storage.save_scenario(owner, build_scenario(ScenarioConfig(seed=seed, duration_seconds=duration)))
    return storage.create_session(owner, operation_id, scenario.scenario_id)


def mutate(view, kind='step', **kwargs):
    return storage.mutate('alice', view.session_id, Command(operation_id=f'op-{view.revision}',
                          expected_revision=view.revision, kind=kind, **kwargs))


@pytest.mark.parametrize('seed', [0, 7, 2147483647])
def test_determinism_to_fulltime_and_legal_events(seed):
    first = until(make_state(seed), 5400)
    second = until(make_state(seed), 5400)
    assert canonical(first) == canonical(second)
    assert first.lifecycle == 'completed'
    assert first.events[-1].type == 'fulltime'
    assert first.pending == []
    assert [e.sequence for e in first.events] == list(range(1, first.event_cursor + 1))
    assert [e.tick for e in first.events] == sorted(e.tick for e in first.events)
    assert any(e.type == 'goal' for e in first.events)
    assert first.score == {t: sum(e.type == 'goal' and e.team_id == t for e in first.events) for t in first.score}
    compatible = match_events(first, 'engine-test')
    from app.analytics import state_at, metrics_at
    match = match_record(first, 'engine-test')
    replay = state_at(match, compatible, 5400)
    metrics = metrics_at(match, compatible, 5400)
    assert replay.score.home == first.score['home'] == metrics.home.goals
    assert replay.score.away == first.score['away'] == metrics.away.goals
    for native, event in zip(first.events, compatible):
        assert event.end.x == (100 - native.end_x if native.team_id == 'away' else native.end_x)


def test_clock_and_batching():
    s = make_state(duration=120)
    s = apply_command(s, command(s, 'resume'))
    assert s.tick == 0 and s.lifecycle == 'running'
    with pytest.raises(EngineError, match='step_requires_pause'):
        apply_command(s, command(s))
    s = apply_command(s, command(s, 'advance', ticks=40))
    s = apply_command(s, command(s, 'pause'))
    assert s.tick == 40
    with pytest.raises(EngineError, match='advance_requires_resume'):
        apply_command(s, command(s, 'advance'))
    s = until(s, 120)
    with pytest.raises(EngineError, match='terminal_session'):
        apply_command(s, command(s, 'resume'))
    one = until(make_state(duration=120), 120)
    many = make_state(duration=120)
    while many.tick < 120:
        many = apply_command(many, command(many, ticks=1))
    assert one.events == many.events and one.rng == many.rng
    assert one.score == many.score and one.pending == many.pending


@pytest.mark.parametrize('boundary', [0, 1, 2699, 2700, 2701, 5399, 5400, 'goal'])
def test_exact_checkpoint_continuation(boundary):
    if boundary == 'goal':
        boundary = next(e.tick for e in until(make_state(), 5400).events if e.type == 'goal')
    original = until(make_state(), boundary)
    snapshot = capture_state(original)
    restored = restore_state(json.loads(canonical(snapshot)))
    cursor = original.event_cursor
    if boundary < 5400:
        intervention = command(original, 'intervene', team_id='home', field='pressing', value=90, requested_tick=original.tick)
        original = apply_command(original, intervention)
        restored = apply_command(restored, intervention)
    original = until(original, 5400)
    restored = until(restored, 5400)
    assert original.events[cursor:] == restored.events[cursor:]
    assert digest(original) == digest(restored)
    assert original.rng == restored.rng and original.pending == restored.pending
    assert snapshot.state.tick == boundary  # checkpoint stayed immutable


def test_intervention_future_only_and_pending_queue_parity():
    s = until(make_state(duration=120), 35)
    history = digest(s.events)
    old = s.tactics['home'].pressing
    changed = apply_command(s, command(s, 'intervene', team_id='home', field='pressing', value=100, requested_tick=35))
    assert changed.tactics['home'].pressing == old
    assert digest(changed.events) == history
    assert changed.pending[0].tick == 36
    restored = restore_state(capture_state(changed))
    assert digest(until(changed, 120)) == digest(until(restored, 120))
    after = until(changed, 36)
    assert after.tactics['home'].pressing == 100
    assert after.interventions[-1].result == 'applied'
    assert digest(after.events[:s.event_cursor]) == history
    assert s.tactics['home'].pressing == old
    with pytest.raises(EngineError, match='stale_tick'):
        apply_command(s, command(s, 'intervene', team_id='home', field='tempo', value=80, requested_tick=34))


def test_tactical_effects_across_paired_seeds():
    totals = {'low_press': 0, 'high_press': 0, 'low_tempo': 0, 'high_tempo': 0}
    for seed in range(10):
        for field, values in [('pressing', [('low_press', 0), ('high_press', 100)]),
                              ('tempo', [('low_tempo', 0), ('high_tempo', 100)])]:
            for name, value in values:
                config = ScenarioConfig(seed=seed, duration_seconds=600)
                setattr(config.home.tactics, field, value)
                setattr(config.away.tactics, field, value)
                result = until(initial_state(build_scenario(config)), 600)
                totals[name] += sum(e.type == 'pressure' if field == 'pressing' else e.type in ('pass', 'carry', 'shot')
                                    for e in result.events)
    assert totals['low_press'] == 0 < totals['high_press']
    assert totals['high_tempo'] > totals['low_tempo']


@pytest.mark.parametrize('field,value', [('formation', '2-2-6'), ('pressing', 101), ('tempo', -1), ('risk', True), ('directness', '50')])
def test_invalid_tactics(field, value):
    with pytest.raises(ValidationError):
        command(make_state(), 'intervene', team_id='home', field=field, value=value, requested_tick=0)


@pytest.mark.parametrize('change', ['missing_rng', 'missing_queue', 'missing_stream', 'queue', 'hash', 'version', 'score', 'role'])
def test_corrupt_snapshots(change):
    s = apply_command(make_state(), command(make_state(), 'intervene', team_id='home', field='tempo', value=90, requested_tick=0))
    data = json.loads(canonical(capture_state(s)))
    if change == 'missing_rng':
        del data['state']['rng']
    elif change == 'missing_queue':
        del data['state']['pending']
    elif change == 'missing_stream':
        del data['state']['rng']['finish']
        data['state_hash'] = digest(data['state'])
    elif change == 'queue':
        data['state']['pending'][0]['tick'] = 0
    elif change == 'hash':
        data['state_hash'] = '0' * 64
    elif change == 'score':
        data['state']['score']['home'] = 99
        data['state_hash'] = digest(data['state'])
    elif change == 'role':
        data['state']['actors'][0]['role'] = 'FW'
        data['state_hash'] = digest(data['state'])
    else:
        data['engine_version'] = 'future/9'
    with pytest.raises(EngineError, match='incompatible_version' if change == 'version' else 'corrupt_snapshot'):
        restore_state(data)


def test_scenarios_presets_roundtrip_validation(database):
    for config in presets().values():
        s = storage.save_scenario('alice', build_scenario(config))
        assert storage.get_scenario('alice', s.scenario_id) == s
        assert build_scenario(ScenarioConfig.model_validate_json(config.model_dump_json())) == s
    c = ScenarioConfig(preset='custom')
    c.home.players[1].player_id = c.home.players[0].player_id
    with pytest.raises(ValidationError):
        build_scenario(c)
    with pytest.raises(ValidationError):
        ScenarioConfig(duration_seconds=59)
    assert build_scenario(ScenarioConfig(seed=8)).config_hash != build_scenario(ScenarioConfig(seed=7)).config_hash


def test_runtime_checkpoint_isolation_manifest_and_restart(database):
    root = runtime()
    root = mutate(root, ticks=40)
    root = mutate(root, 'intervene', team_id='home', field='formation', value='3-5-2', requested_tick=40)
    root = mutate(root, 'checkpoint')
    checkpoint = storage.get_checkpoint('alice', root.checkpoint_id)
    branch = storage.create_session('alice', 'fork', checkpoint_id=root.checkpoint_id, expected_revision=root.revision)
    before = storage.get_runtime('alice', root.session_id)
    assert before.state.pending
    assert digest(before.state) == branch.state_hash
    root = mutate(root, ticks=80)
    branch = mutate(branch, ticks=80)
    assert root.state_hash == branch.state_hash and root.event_hash == branch.event_hash
    assert verify_manifest(storage.manifest('alice', root.session_id)).verified
    assert verify_manifest(storage.manifest('alice', branch.session_id)).verified
    assert storage.get_checkpoint('alice', checkpoint.checkpoint_id) == checkpoint
    # Independent connections reread disk; a separate runtime does not share references.
    view = storage.get_runtime('alice', branch.session_id)
    view.state.score['home'] += 50
    assert storage.get_runtime('alice', branch.session_id).state.score != view.state.score
    assert storage.get_runtime('alice', root.session_id).state_hash == root.state_hash
    assert storage.get_runtime('alice', branch.session_id).revision == branch.revision
    with pytest.raises(EngineError, match='not_found'):
        storage.get_runtime('bob', root.session_id)
    with pytest.raises(EngineError, match='not_found'):
        storage.get_checkpoint('bob', checkpoint.checkpoint_id)
    with pytest.raises(EngineError, match='stale_revision'):
        storage.create_session('alice', 'bad-fork', checkpoint_id=checkpoint.checkpoint_id, expected_revision=0)


def test_divergent_branch_preserves_parent(database):
    parent = mutate(runtime(duration=600), ticks=50)
    parent = mutate(parent, 'checkpoint')
    child = storage.create_session('alice', 'fork', checkpoint_id=parent.checkpoint_id, expected_revision=parent.revision)
    child = mutate(child, 'intervene', team_id='home', field='pressing', value=100, requested_tick=50)
    child = mutate(child, ticks=300)
    assert storage.get_runtime('alice', parent.session_id).state_hash == parent.state_hash
    assert digest(storage.get_runtime('alice', child.session_id).state.events[:parent.event_cursor]) == parent.event_hash
    assert verify_manifest(storage.manifest('alice', child.session_id)).verified


@pytest.mark.parametrize('same_command', [True, False])
def test_concurrent_revision_and_idempotency(database, same_command):
    root = runtime()
    barrier = Barrier(4)

    def attempt(i):
        barrier.wait(timeout=10)
        c = Command(operation_id='same' if same_command else f'worker-{i}', expected_revision=0, kind='step', ticks=10)
        try:
            return storage.mutate('alice', root.session_id, c)
        except EngineError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, range(4)))
    assert storage.get_runtime('alice', root.session_id).tick == 10
    assert storage.get_runtime('alice', root.session_id).revision == 1
    if same_command:
        assert all(r == results[0] for r in results)
    else:
        assert results.count('stale_revision') == 3
    with storage.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM commands').fetchone()[0] == 1


def test_lost_response_retry_conflicting_key_and_cursor(database):
    original = runtime()
    cmd = Command(operation_id='lost', expected_revision=0, kind='step', ticks=60)
    receipt = storage.mutate('alice', original.session_id, cmd)
    mutate(receipt, ticks=10)
    assert storage.mutate('alice', original.session_id, cmd) == receipt
    assert runtime() == original
    with pytest.raises(EngineError, match='idempotency_conflict'):
        storage.mutate('alice', original.session_id, cmd.model_copy(update={'ticks': 10}))
    seen, cursor = [], 0
    while True:
        page = storage.read_events('alice', original.session_id, cursor, 3)
        seen.extend(page.events)
        cursor = page.next_cursor
        if cursor == page.event_cursor:
            break
    assert seen == storage.get_runtime('alice', original.session_id).state.events
    assert not storage.read_events('alice', original.session_id, cursor, 3).events
    with pytest.raises(EngineError, match='cursor_ahead'):
        storage.read_events('alice', original.session_id, cursor + 1, 3)


def test_interrupted_transaction_rolls_back_state_events_checkpoint_and_ack(database, monkeypatch):
    root = mutate(runtime(), ticks=20)
    before = storage.get_runtime('alice', root.session_id)
    original_capture = storage.capture_state

    def fail(_):
        raise sqlite3.OperationalError('injected interruption after state and command writes')

    monkeypatch.setattr(storage, 'capture_state', fail)
    cmd = Command(operation_id='retry-checkpoint', expected_revision=root.revision, kind='checkpoint')
    with pytest.raises(sqlite3.OperationalError):
        storage.mutate('alice', root.session_id, cmd)
    assert storage.get_runtime('alice', root.session_id) == before
    with storage.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM commands').fetchone()[0] == 1
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    monkeypatch.setattr(storage, 'capture_state', original_capture)
    assert storage.mutate('alice', root.session_id, cmd).checkpoint_id


@pytest.mark.parametrize('tamper', ['seed', 'intervention', 'event', 'state', 'ancestry'])
def test_manifest_tampering(database, tamper):
    root = mutate(runtime(), ticks=20)
    root = mutate(root, 'checkpoint')
    branch = storage.create_session('alice', 'fork', checkpoint_id=root.checkpoint_id, expected_revision=root.revision)
    branch = mutate(branch, 'intervene', team_id='home', field='pressing', value=100, requested_tick=20)
    branch = mutate(branch, ticks=100)
    data = storage.manifest('alice', branch.session_id).model_dump(mode='json')
    if tamper == 'seed':
        data['scenario']['config']['seed'] += 1
    elif tamper == 'intervention':
        data['operations'][2]['command']['value'] = 0
    elif tamper == 'event':
        data['event_hashes'][3] = '0' * 64
    elif tamper == 'state':
        data['state_hash'] = '0' * 64
    else:
        data['ancestry'][0]['snapshot_hash'] = '0' * 64
    result = verify_manifest(ExperimentManifest.model_validate(data))
    assert not result.verified and result.component


def test_cli_verifier_in_separate_process(database):
    root = mutate(runtime(), ticks=120)
    path = database / 'experiment.json'
    path.write_text(canonical(storage.manifest('alice', root.session_id)), encoding='utf-8')
    result = subprocess.run([sys.executable, '-m', 'app.sandbox.verify_manifest', str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['verified']
    data = json.loads(path.read_text())
    data['engine_version'] = 'future/2'
    path.write_text(json.dumps(data))
    result = subprocess.run([sys.executable, '-m', 'app.sandbox.verify_manifest', str(path)], capture_output=True, text=True)
    assert result.returncode == 1
    assert json.loads(result.stdout)['component'] == 'schema_or_version'


def test_api_authorization_contract_journey_and_rejection_audit(database, monkeypatch):
    monkeypatch.setenv('PULSE_RUNTIME_TOKENS', json.dumps({'alice': 'a' * 32, 'bob': 'b' * 32}))
    with TestClient(app) as client:
        headers = {'Authorization': 'Bearer ' + 'a' * 32}
        assert client.post('/api/sandbox/scenarios', json={}).status_code == 403
        response = client.post('/api/sandbox/scenarios', headers=headers, json={'duration_seconds': 120})
        assert response.status_code == 200, response.text
        scenario = response.json()
        root = client.post('/api/sandbox/sessions', headers=headers, json={'operation_id': 'http-create', 'scenario_id': scenario['scenario_id']}).json()
        route = f"/api/sandbox/sessions/{root['session_id']}"
        request = {'operation_id': 'step', 'expected_revision': 0, 'kind': 'step', 'ticks': 60}
        updated = client.post(route + '/commands', headers=headers, json=request)
        assert updated.status_code == 200, updated.text
        assert updated.json()['tick'] == 60 and updated.json()['revision'] == 1
        assert client.post(route + '/commands', headers=headers, json=request).json() == updated.json()
        request['operation_id'] = 'stale'
        assert client.post(route + '/commands', headers=headers, json=request).json()['detail']['code'] == 'stale_revision'
        assert client.get(route + '/audit', headers=headers).json()[-1]['result'] == 'rejected'
        assert client.get(route + '/state', headers={'Authorization': 'Bearer ' + 'b' * 32}).status_code == 404
        checkpoint = client.post(route + '/commands', headers=headers, json={'operation_id': 'save', 'expected_revision': 1, 'kind': 'checkpoint'}).json()
        cp_route = '/api/sandbox/checkpoints/' + checkpoint['checkpoint_id']
        assert client.get(cp_route, headers=headers).json()['snapshot']['state']['rng']
        fork = client.post(cp_route + '/restore', headers=headers, json={'operation_id': 'fork', 'expected_revision': 2})
        assert fork.status_code == 200 and fork.json()['session_id'] != root['session_id']
        manifest = client.get(route + '/manifest', headers=headers).json()
        assert client.post('/api/sandbox/verify', headers=headers, json=manifest).json()['verified']
        assert client.get(route + '/events', headers=headers).json()['event_cursor'] == updated.json()['event_cursor']
        assert client.post('/api/sandbox/scenarios', headers={**headers, 'Content-Type': 'application/json'}, content='{"seed":1,"seed":2}').status_code == 400
        assert client.post(route + '/commands', headers=headers, json={**request, 'ticks': 301}).status_code == 422
        assert client.get(route + '/match-events', headers=headers).status_code == 422  # v1 only represents 90-minute matches


def test_cancel_limits_and_database_separation(database, monkeypatch):
    root = runtime()
    root = mutate(root, 'cancel')
    assert root.lifecycle == 'cancelled'
    with pytest.raises(EngineError, match='terminal_session'):
        mutate(root)
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(database / 'data.sqlite'))
    with pytest.raises(RuntimeError, match='separate'):
        storage.runtime_database_path()


def test_durable_recovery_in_another_process(database):
    root = mutate(runtime(), ticks=30)
    root = mutate(root, 'checkpoint')
    code = ('from app.sandbox.storage import get_runtime; '
            f"v=get_runtime('alice','{root.session_id}'); print(v.state_hash)")
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == root.state_hash


def test_runtime_backup_roundtrip_preserves_datahub(database, monkeypatch):
    from app.sandbox.backup import copy_database
    from app.storage import connect as data_connect
    with data_connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
    root = mutate(runtime(), ticks=60)
    root = mutate(root, 'checkpoint')
    target = database / 'backup.sqlite'
    result = copy_database(storage.runtime_database_path(), target)
    recovered = database / 'recovered.sqlite'
    copy_database(target, recovered, result['sha256'])
    with pytest.raises(FileExistsError):
        copy_database(target, recovered)
    with pytest.raises(ValueError, match='checksum'):
        copy_database(target, database / 'invalid.sqlite', '0' * 64)
    monkeypatch.setenv('PULSE_RUNTIME_DB_PATH', str(recovered))
    assert storage.get_runtime('alice', root.session_id).state_hash == root.state_hash
    assert storage.get_checkpoint('alice', root.checkpoint_id).tick == 60
    with data_connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='sessions'").fetchone()


def test_atomic_migration_and_concurrent_cold_start(database, monkeypatch):
    original = storage.DDL
    monkeypatch.setattr(storage, 'DDL', original[:2] + ('INVALID SQL',))
    with pytest.raises(sqlite3.OperationalError):
        with storage.connect():
            pass
    raw = sqlite3.connect(storage.runtime_database_path())
    assert raw.execute('PRAGMA user_version').fetchone()[0] == 0
    assert not raw.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    raw.close()
    monkeypatch.setattr(storage, 'DDL', original)
    barrier = Barrier(6)

    def read(_):
        barrier.wait(timeout=10)
        with storage.connect() as db:
            return db.execute('PRAGMA user_version').fetchone()[0]

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert list(pool.map(read, range(6))) == [2] * 6


def test_concurrent_restore_isolated_and_duplicate_creation(database):
    root = mutate(runtime(), 'checkpoint')
    barrier = Barrier(4)

    def restore(i):
        barrier.wait(timeout=10)
        return storage.create_session('alice', f'fork-{i // 2}', checkpoint_id=root.checkpoint_id,
                                      expected_revision=root.revision)

    with ThreadPoolExecutor(max_workers=4) as pool:
        branches = list(pool.map(restore, range(4)))
    assert branches[0] == branches[1] and branches[2] == branches[3]
    assert branches[0].session_id != branches[2].session_id
    mutate(branches[0], ticks=50)
    assert storage.get_runtime('alice', branches[2].session_id).tick == 0
    assert storage.get_runtime('alice', root.session_id).tick == 0


def test_api_safe_transaction_failure_and_auth_configuration(database, monkeypatch):
    monkeypatch.delenv('PULSE_RUNTIME_TOKENS', raising=False)
    monkeypatch.delenv('PULSE_RUNTIME_TOKEN', raising=False)
    client = TestClient(app)
    assert client.get('/api/sandbox/versions').status_code == 503
    monkeypatch.setenv('PULSE_RUNTIME_TOKEN', 'c' * 32)
    headers = {'Authorization': 'Bearer ' + 'c' * 32}
    root = runtime(owner='operator')

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError('internal SQL details must not leak')

    monkeypatch.setattr(storage, 'mutate', fail)
    response = client.post(f'/api/sandbox/sessions/{root.session_id}/commands', headers=headers,
                           json={'operation_id': 'fail', 'expected_revision': 0, 'kind': 'step'})
    assert response.status_code == 503
    assert response.json() == {'detail': {'code': 'transaction_failed'}}


def test_committed_golden_and_manifest_examples():
    root = Path(__file__).resolve().parents[2] / 'docs' / 'examples' / 'sandbox'
    expected = json.loads((root / 'golden.json').read_text())
    result = until(make_state(expected['seed']), 5400)
    assert digest(result) == expected['state_hash']
    assert digest(result.events) == expected['event_hash']
    assert result.score == expected['score']
    manifest = ExperimentManifest.model_validate_json((root / 'experiment.json').read_bytes())
    assert verify_manifest(manifest).verified


@pytest.mark.parametrize('field,value', [('formation', '3-5-2'), ('directness', 100), ('risk', 100), ('compactness', 100)])
def test_each_supported_policy_changes_real_future_actions(field, value):
    effects = []
    for seed in range(5):
        baseline = until(make_state(seed=seed, duration=600), 50)
        intervention = command(baseline, 'intervene', team_id='home', field=field, value=value, requested_tick=50)
        changed = apply_command(baseline, intervention)
        before_count = len(baseline.events)
        baseline, changed = until(baseline, 600), until(changed, 600)
        assert baseline.events[:before_count] == changed.events[:before_count]
        # Ignore policy-revision annotations. A threshold change need not cross a
        # draw in every short trial; test its behavior across a fixed seed set.
        def behavior(s):
            return [(e.type, e.actor_id, e.outcome, e.end_x, e.end_y) for e in s.events[before_count:]]
        effects.append(behavior(baseline) != behavior(changed))
    assert any(effects)


def test_interrupted_event_append_rolls_back_all_writes(database):
    root = runtime()
    before = storage.get_runtime('alice', root.session_id)
    with storage.connect() as db:
        db.execute("CREATE TRIGGER injected_failure BEFORE INSERT ON commands BEGIN SELECT RAISE(ABORT,'injected'); END")
    cmd = Command(operation_id='step-after-interruption', expected_revision=0, kind='step', ticks=50)
    with pytest.raises(sqlite3.IntegrityError):
        storage.mutate('alice', root.session_id, cmd)
    assert storage.get_runtime('alice', root.session_id) == before
    assert storage.read_events('alice', root.session_id, 0, 100).event_cursor == 1
    with storage.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM commands').fetchone()[0] == 0
        db.execute('DROP TRIGGER injected_failure')
    assert storage.mutate('alice', root.session_id, cmd).tick == 50


def test_bounded_sessions_and_invalid_future_database(database):
    root = runtime()
    with storage.connect() as db:
        row = db.execute('SELECT * FROM sessions WHERE id=?', (root.session_id,)).fetchone()
        db.executemany('INSERT INTO sessions VALUES (?,?,?,?,?,?)',
                       [(f'capacity-{i}', *row[1:]) for i in range(99)])
    with pytest.raises(EngineError, match='session_limit'):
        runtime(operation_id='overflow')
    assert runtime() == root  # retries work at capacity
    with storage.connect() as db:
        db.execute('PRAGMA user_version=99')
    with pytest.raises(RuntimeError, match='unsupported'):
        storage.get_runtime('alice', root.session_id)
