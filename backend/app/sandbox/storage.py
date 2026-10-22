"""Dedicated runtime DB, schema 4. Never migrate or reinterpret the data-hub DB.

Every command, appended events, checkpoint and acknowledgment commits together.
BEGIN IMMEDIATE serializes workers/processes; Python memory is never the authority.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from ..storage import database_path, enable_wal
from .engine import (EngineError, apply_command, canonical, capture_state, digest, initial_state,
                     restore_state, validate_state, implementation_hash)
from .models import (Ancestor, AuditEntry, Command, EngineState, EventPage,
                     ExperimentManifest, MutationResult, ReplayRecord, RuntimeView, Scenario, Snapshot)
from .checkpoint_metadata import StoredCheckpoint
from .scenario_archive import ScenarioArchive, ScenarioSummary, utc_now, validate_identity

DDL = (
    'CREATE TABLE scenarios (owner TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(owner,id))',
    '''CREATE TABLE sessions (id TEXT PRIMARY KEY, owner TEXT NOT NULL, creation_hash TEXT NOT NULL,
       payload TEXT NOT NULL, prefix TEXT NOT NULL, ancestry TEXT NOT NULL)''',
    '''CREATE TABLE commands (session_id TEXT NOT NULL REFERENCES sessions(id), operation_id TEXT NOT NULL,
       fingerprint TEXT NOT NULL, record TEXT NOT NULL, ack TEXT NOT NULL, revision INTEGER NOT NULL,
       PRIMARY KEY(session_id,operation_id), UNIQUE(session_id,revision))''',
    '''CREATE TABLE runtime_events (session_id TEXT NOT NULL REFERENCES sessions(id), cursor INTEGER NOT NULL,
       payload TEXT NOT NULL, PRIMARY KEY(session_id,cursor))''',
    '''CREATE TABLE checkpoints (id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
       owner TEXT NOT NULL, payload TEXT NOT NULL, records TEXT NOT NULL, ancestry TEXT NOT NULL)''',
    '''CREATE TABLE audit (session_id TEXT NOT NULL REFERENCES sessions(id), fingerprint TEXT NOT NULL,
       payload TEXT NOT NULL, PRIMARY KEY(session_id,fingerprint))''',
)

CONTROL_DDL = (
    '''CREATE TABLE runs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, fingerprint TEXT NOT NULL,
       session_id TEXT NOT NULL REFERENCES sessions(id), generation INTEGER NOT NULL, payload TEXT NOT NULL)''',
    '''CREATE TABLE experiments (id TEXT PRIMARY KEY, owner TEXT NOT NULL, fingerprint TEXT NOT NULL,
       generation INTEGER NOT NULL, payload TEXT NOT NULL)''',
)

SCENARIO_METADATA_DDL = (
    '''CREATE TABLE scenario_metadata (owner TEXT NOT NULL, id TEXT NOT NULL, created_at_utc TEXT,
       PRIMARY KEY(owner,id), FOREIGN KEY(owner,id) REFERENCES scenarios(owner,id))''',
    'INSERT INTO scenario_metadata(owner,id,created_at_utc) SELECT owner,id,NULL FROM scenarios',
)


CHECKPOINT_METADATA_DDL = (
    'CREATE TABLE checkpoint_metadata (id TEXT PRIMARY KEY REFERENCES checkpoints(id), created_at_utc TEXT)',
    'INSERT INTO checkpoint_metadata(id,created_at_utc) SELECT id,NULL FROM checkpoints',
)


def runtime_database_path() -> Path:
    path = Path(os.getenv('PULSE_RUNTIME_DB_PATH', str(database_path().with_name('pulse_runtime.sqlite'))))
    if path.resolve() == database_path().resolve():
        raise RuntimeError('runtime DB must be separate from imported match DB')
    return path


@contextmanager
def connect():
    path = runtime_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        enable_wal(db)
        if db.execute('PRAGMA user_version').fetchone()[0] == 0:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('PRAGMA user_version').fetchone()[0] == 0:
                for statement in DDL:
                    db.execute(statement)
                db.execute('PRAGMA user_version=1')
            db.commit()
        if db.execute('PRAGMA user_version').fetchone()[0] == 1:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('PRAGMA user_version').fetchone()[0] == 1:
                for statement in CONTROL_DDL:
                    db.execute(statement)
                db.execute('PRAGMA user_version=2')
            db.commit()
        if db.execute('PRAGMA user_version').fetchone()[0] == 2:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('PRAGMA user_version').fetchone()[0] == 2:
                for statement in SCENARIO_METADATA_DDL:
                    db.execute(statement)
                db.execute('PRAGMA user_version=3')
            db.commit()
        if db.execute('PRAGMA user_version').fetchone()[0] == 3:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('PRAGMA user_version').fetchone()[0] == 3:
                for statement in CHECKPOINT_METADATA_DDL:
                    db.execute(statement)
                db.execute('PRAGMA user_version=4')
            db.commit()
        if db.execute('PRAGMA user_version').fetchone()[0] != 4:
            raise RuntimeError('unsupported runtime database version')
        with db:
            yield db
    finally:
        db.close()


def load(db, owner, session_id):
    row = db.execute('SELECT payload,prefix,ancestry FROM sessions WHERE id=? AND owner=?', (session_id, owner)).fetchone()
    if row is None:
        raise EngineError('not_found', 404)
    state = EngineState.model_validate_json(row[0])
    validate_state(state)
    return state, json.loads(row[1]), json.loads(row[2])


def records(db, session_id, prefix):
    return prefix + [json.loads(row[0]) for row in db.execute(
        'SELECT record FROM commands WHERE session_id=? ORDER BY revision', (session_id,))]


def ack(state, session_id, checkpoint_id=None):
    return MutationResult(session_id=session_id, scenario_id=state.scenario.scenario_id,
        tick=state.tick, revision=state.revision, event_cursor=state.event_cursor, lifecycle=state.lifecycle,
        state_hash=digest(state), event_hash=digest(state.events), checkpoint_id=checkpoint_id)


def save_scenario(owner: str, scenario: Scenario) -> Scenario:
    return _save_scenario(owner, ScenarioArchive(scenario=scenario, created_at_utc=utc_now()))


def _save_scenario(owner: str, archive: ScenarioArchive) -> Scenario:
    scenario = validate_identity(archive)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT payload FROM scenarios WHERE owner=? AND id=?', (owner, scenario.scenario_id)).fetchone()
        if existing:
            if existing[0] != canonical(scenario):
                raise EngineError('scenario_conflict')
            return scenario
        if db.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0] >= 100:
            raise EngineError('scenario_limit', 429)
        db.execute('INSERT INTO scenarios VALUES (?,?,?)', (owner, scenario.scenario_id, canonical(scenario)))
        db.execute('INSERT INTO scenario_metadata VALUES (?,?,?)', (owner, scenario.scenario_id, archive.created_at_utc))
    return scenario


def get_scenario_archive(owner: str, scenario_id: str) -> ScenarioArchive:
    with connect() as db:
        row = db.execute('''SELECT s.payload,m.created_at_utc FROM scenarios s JOIN scenario_metadata m
            ON s.owner=m.owner AND s.id=m.id WHERE s.owner=? AND s.id=?''', (owner, scenario_id)).fetchone()
        if row is None:
            raise EngineError('not_found', 404)
        result = ScenarioArchive(scenario=Scenario.model_validate_json(row[0]), created_at_utc=row[1])
        validate_identity(result)
        return result


def import_scenario(owner: str, archive: ScenarioArchive) -> ScenarioArchive:
    scenario = _save_scenario(owner, archive)
    # Identical imports retain the first stored creation metadata.
    return get_scenario_archive(owner, scenario.scenario_id)


def list_scenarios(owner: str) -> list[ScenarioSummary]:
    with connect() as db:
        rows = db.execute('''SELECT s.payload,m.created_at_utc FROM scenarios s JOIN scenario_metadata m
            ON s.owner=m.owner AND s.id=m.id WHERE s.owner=? ORDER BY s.id LIMIT 100''', (owner,)).fetchall()
        result = []
        for payload, created in rows:
            scenario = Scenario.model_validate_json(payload)
            result.append(ScenarioSummary(scenario_id=scenario.scenario_id, config_hash=scenario.config_hash,
                seed=scenario.config.seed, preset=scenario.config.preset, created_at_utc=created))
        return result


def get_scenario(owner: str, scenario_id: str) -> Scenario:
    with connect() as db:
        row = db.execute('SELECT payload FROM scenarios WHERE owner=? AND id=?', (owner, scenario_id)).fetchone()
        if not row:
            raise EngineError('not_found', 404)
        return Scenario.model_validate_json(row[0])


def create_session(owner: str, operation_id: str, scenario_id: str | None = None,
                   checkpoint_id: str | None = None, expected_revision: int | None = None) -> MutationResult:
    # Client operation ID defines creation identity; changing the input is a conflict.
    session_id = 'runtime-' + digest([owner, operation_id])
    fingerprint = digest([scenario_id, checkpoint_id, expected_revision])
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT creation_hash FROM sessions WHERE id=? AND owner=?', (session_id, owner)).fetchone()
        if existing:
            if existing[0] != fingerprint:
                raise EngineError('idempotency_conflict')
            # Reconcile creation to its original boundary, even after later commands.
            row = db.execute('SELECT payload FROM runtime_events WHERE session_id=? AND cursor=0', (session_id,)).fetchone()
            return MutationResult.model_validate_json(row[0])
        if db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] >= 100:
            raise EngineError('session_limit', 429)
        prefix, ancestry = [], []
        if checkpoint_id:
            row = db.execute('SELECT session_id,payload,records,ancestry FROM checkpoints WHERE id=? AND owner=?', (checkpoint_id, owner)).fetchone()
            if row is None:
                raise EngineError('not_found', 404)
            state = restore_state(json.loads(row[1]))
            if state.revision != expected_revision:
                raise EngineError('stale_revision')
            prefix, ancestry = json.loads(row[2]), json.loads(row[3])
            if len(ancestry) >= 32:
                raise EngineError('ancestry_limit', 429)
            ancestry.append(Ancestor(checkpoint_id=checkpoint_id, session_id=row[0],
                                     snapshot_hash=digest(state), revision=state.revision).model_dump())
        else:
            row = db.execute('SELECT payload FROM scenarios WHERE owner=? AND id=?', (owner, scenario_id)).fetchone()
            if row is None:
                raise EngineError('not_found', 404)
            state = initial_state(Scenario.model_validate_json(row[0]))
        db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?)',
                   (session_id, owner, fingerprint, canonical(state), canonical(prefix), canonical(ancestry)))
        result = ack(state, session_id)
        # Cursor zero is a private creation receipt, excluded from event delivery.
        db.execute('INSERT INTO runtime_events VALUES (?,?,?)', (session_id, 0, canonical(result)))
        db.executemany('INSERT INTO runtime_events VALUES (?,?,?)',
                       [(session_id, e.sequence, canonical(e)) for e in state.events])
        return result


def get_runtime(owner: str, session_id: str) -> RuntimeView:
    with connect() as db:
        state, _, _ = load(db, owner, session_id)
        return RuntimeView(**{k: v for k, v in ack(state, session_id).model_dump().items() if k != 'lifecycle'}, state=state)


def runtime_revision(owner: str, session_id: str) -> int:
    """Read the committed boundary without parsing an unchanged event snapshot.

    Restored branches start at their creation receipt's inherited revision; local
    command revisions advance atomically with the state. Keep ownership in this
    query even when an observer has already authenticated.
    """
    with connect() as db:
        row = db.execute('''SELECT
            (SELECT MAX(c.revision) FROM commands c WHERE c.session_id=s.id), e.payload
            FROM sessions s JOIN runtime_events e ON e.session_id=s.id AND e.cursor=0
            WHERE s.id=? AND s.owner=?''', (session_id, owner)).fetchone()
        if row is None:
            raise EngineError('not_found', 404)
        revision = row[0] if row[0] is not None else json.loads(row[1])['revision']
        if type(revision) is not int or revision < 0:
            raise EngineError('runtime_revision_invalid', 500)
        return revision


def read_events(owner: str, session_id: str, cursor: int, limit: int) -> EventPage:
    with connect() as db:
        db.execute('BEGIN')
        state, _, _ = load(db, owner, session_id)
        if cursor > state.event_cursor:
            raise EngineError('cursor_ahead')
        values = [json.loads(r[0]) for r in db.execute(
            'SELECT payload FROM runtime_events WHERE session_id=? AND cursor>? ORDER BY cursor LIMIT ?',
            (session_id, cursor, limit))]
        return EventPage(session_id=session_id, tick=state.tick, revision=state.revision,
            event_cursor=state.event_cursor, next_cursor=values[-1]['sequence'] if values else cursor, events=values)


def mutate(owner: str, session_id: str, command: Command) -> MutationResult:
    failure = None
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        state, prefix, ancestry = load(db, owner, session_id)
        # Preserve retry fingerprints for schema-1 commands written before the
        # optional paired-trial field existed.
        fingerprint = digest({k: v for k, v in command.model_dump(mode='json').items()
                              if k != 'trial_index' or v is not None})
        existing = db.execute('SELECT fingerprint,ack FROM commands WHERE session_id=? AND operation_id=?',
                              (session_id, command.operation_id)).fetchone()
        if existing:
            if existing[0] != fingerprint:
                raise EngineError('idempotency_conflict')
            return MutationResult.model_validate_json(existing[1])
        if any(r['command']['operation_id'] == command.operation_id for r in prefix):
            raise EngineError('inherited_operation_id')
        audit_count = db.execute('SELECT COUNT(*) FROM audit WHERE session_id=?', (session_id,)).fetchone()[0]
        if audit_count >= 4096:
            raise EngineError('audit_limit', 429)
        rejected = db.execute('SELECT payload FROM audit WHERE session_id=? AND fingerprint=?', (session_id, fingerprint)).fetchone()
        if rejected:
            previous = json.loads(rejected[0])
            raise EngineError(previous['code'], previous['status_code'])
        try:
            updated = apply_command(state, command)
            if command.kind == 'checkpoint' and db.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0] >= 200:
                raise EngineError('checkpoint_limit', 429)
        except EngineError as error:
            failure = error
            entry = AuditEntry(session_id=session_id, scenario_id=state.scenario.scenario_id, command=command,
                result='rejected', code=error.code, status_code=error.status, tick=state.tick, revision=state.revision, event_cursor=state.event_cursor)
            db.execute('INSERT INTO audit VALUES (?,?,?)', (session_id, fingerprint, canonical(entry)))
        else:
            checkpoint_id = 'checkpoint-' + digest([session_id, command.operation_id]) if command.kind == 'checkpoint' else None
            result = ack(updated, session_id, checkpoint_id)
            record = ReplayRecord(command=command, state_hash=result.state_hash, event_hash=result.event_hash)
            db.execute('UPDATE sessions SET payload=? WHERE id=?', (canonical(updated), session_id))
            db.executemany('INSERT INTO runtime_events VALUES (?,?,?)',
                [(session_id, e.sequence, canonical(e)) for e in updated.events[state.event_cursor:]])
            db.execute('INSERT INTO commands VALUES (?,?,?,?,?,?)',
                (session_id, command.operation_id, fingerprint, canonical(record), canonical(result), updated.revision))
            if checkpoint_id:
                db.execute('INSERT INTO checkpoints VALUES (?,?,?,?,?,?)',
                    (checkpoint_id, session_id, owner, canonical(capture_state(updated)),
                     canonical(records(db, session_id, prefix)), canonical(ancestry)))
                db.execute('INSERT INTO checkpoint_metadata VALUES (?,?)', (checkpoint_id, utc_now()))
            entry = AuditEntry(session_id=session_id, scenario_id=state.scenario.scenario_id, command=command,
                result='accepted', tick=updated.tick, revision=updated.revision, event_cursor=updated.event_cursor,
                intervention=updated.interventions[-1] if command.kind == 'intervene' else None)
            db.execute('INSERT INTO audit VALUES (?,?,?)', (session_id, fingerprint, canonical(entry)))
    if failure:
        raise failure
    return result


def get_checkpoint(owner: str, checkpoint_id: str) -> StoredCheckpoint:
    with connect() as db:
        row = db.execute('SELECT c.session_id,c.payload,m.created_at_utc FROM checkpoints c JOIN checkpoint_metadata m ON c.id=m.id WHERE c.id=? AND c.owner=?', (checkpoint_id, owner)).fetchone()
        if row is None:
            raise EngineError('not_found', 404)
        payload = json.loads(row[1])
        state = restore_state(payload)
        snapshot = Snapshot.model_validate(payload)
        return StoredCheckpoint(created_at_utc=row[2], checkpoint_id=checkpoint_id, session_id=row[0], scenario_id=state.scenario.scenario_id,
                              tick=state.tick, revision=state.revision, event_cursor=state.event_cursor, snapshot=snapshot)


def audit_log(owner: str, session_id: str) -> list[AuditEntry]:
    with connect() as db:
        load(db, owner, session_id)
        return [AuditEntry.model_validate_json(r[0]) for r in db.execute(
            'SELECT payload FROM audit WHERE session_id=? ORDER BY rowid', (session_id,))]


def manifest(owner: str, session_id: str) -> ExperimentManifest:
    with connect() as db:
        db.execute('BEGIN')
        state, prefix, ancestry = load(db, owner, session_id)
        return ExperimentManifest(session_id=session_id, scenario=state.scenario, ancestry=ancestry, implementation_hash=implementation_hash(),
            operations=records(db, session_id, prefix), interventions=state.interventions,
            event_hashes=[digest(e) for e in state.events], state_hash=digest(state), event_hash=digest(state.events))


def list_checkpoints(owner: str, session_id: str) -> list[dict]:
    with connect() as db:
        load(db, owner, session_id)
        result = []
        for cid, payload, created in db.execute('SELECT c.id,c.payload,m.created_at_utc FROM checkpoints c JOIN checkpoint_metadata m ON c.id=m.id WHERE c.session_id=? AND c.owner=? ORDER BY c.rowid', (session_id, owner)):
            snapshot = Snapshot.model_validate_json(payload)
            s = snapshot.state
            result.append({'checkpoint_id': cid, 'session_id': session_id, 'scenario_id': s.scenario.scenario_id,
                           'tick': s.tick, 'revision': s.revision, 'event_cursor': s.event_cursor, 'state_hash': snapshot.state_hash,
                           'lifecycle': s.lifecycle, 'created_at_utc': created})
        return result


def list_sessions(owner: str) -> list[dict]:
    with connect() as db:
        return [{'session_id': sid, 'scenario_id': scenario, 'tick': tick, 'revision': revision,
                 'event_cursor': cursor, 'lifecycle': lifecycle} for sid, scenario, tick, revision, cursor, lifecycle in db.execute(
            "SELECT id,json_extract(payload,'$.scenario.scenario_id'),json_extract(payload,'$.tick'),"
            "json_extract(payload,'$.revision'),json_extract(payload,'$.event_cursor'),json_extract(payload,'$.lifecycle') "
            'FROM sessions WHERE owner=? ORDER BY rowid DESC', (owner,))]


def manifest_at(owner: str, session_id: str, revision: int) -> ExperimentManifest:
    """Reconstruct an immutable committed boundary, even if a branch progressed."""
    current = manifest(owner, session_id)
    if revision < 0 or revision > len(current.operations):
        raise EngineError('revision_not_found', 404)
    operations = current.operations[:revision]
    state = initial_state(current.scenario)
    for record in operations:
        state = apply_command(state, record.command)
        if digest(state) != record.state_hash or digest(state.events) != record.event_hash:
            raise EngineError('history_diverged', 422)
    return ExperimentManifest(session_id=session_id, scenario=state.scenario, implementation_hash=implementation_hash(),
        ancestry=[a for a in current.ancestry if a.revision <= revision], operations=operations,
        interventions=state.interventions, event_hashes=[digest(e) for e in state.events],
        state_hash=digest(state), event_hash=digest(state.events))


def history_at(owner: str, session_id: str, at_tick: int) -> dict:
    """Read-only seek: nearest owned checkpoint, then actual inputs up to cutoff."""
    with connect() as db:
        db.execute('BEGIN')
        source, prefix, _ = load(db, owner, session_id)
        if not 0 <= at_tick <= source.tick:
            raise EngineError('tick_ahead', 409)
        history = records(db, session_id, prefix)
        saved = [Snapshot.model_validate_json(r[0]) for r in db.execute(
            'SELECT payload FROM checkpoints WHERE owner=? AND session_id=?', (owner, session_id))]
    eligible = [s for s in saved if s.state.tick <= at_tick]
    nearest = max(eligible, key=lambda s: (s.state.tick, s.state.revision)) if eligible else None
    state = restore_state(nearest) if nearest else initial_state(source.scenario)
    for record in history[state.revision:]:
        command = Command.model_validate(record['command'])
        if command.kind in ('step', 'advance') and state.tick + command.ticks > at_tick:
            remaining = at_tick - state.tick
            if remaining:
                state = apply_command(state, command.model_copy(update={'ticks': remaining}))
            break
        state = apply_command(state, command)
    return {'session_id': session_id, 'source_revision': source.revision, 'at_tick': at_tick,
            'read_only': True, 'snapshot': capture_state(state)}
