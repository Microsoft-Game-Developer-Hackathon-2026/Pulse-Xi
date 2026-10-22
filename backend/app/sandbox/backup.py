"""Trusted offline runtime backup/restore to NEW files; no web upload surface.

python -m app.sandbox.backup backup source.sqlite new.sqlite
python -m app.sandbox.backup restore backup.sqlite recovered.sqlite --sha256 HASH
"""
import argparse
import json
import os
import sqlite3
from pathlib import Path

from ..database_backup import sha256_file
from .engine import EngineError, canonical, digest, restore_state, implementation_hash, build_scenario
from .manifest import verify_manifest
from .models import EngineState, ExperimentManifest, Scenario
from .storage import records
from .control import Run, Experiment
from .scenario_archive import ScenarioArchive
from .checkpoint_metadata import CheckpointMetadata

TABLES = {'scenarios', 'sessions', 'commands', 'runtime_events', 'checkpoints', 'audit'}


def validate_database(db: sqlite3.Connection) -> dict:
    db.execute('PRAGMA trusted_schema=OFF')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version not in (1, 2, 3, 4):
        raise ValueError('unsupported runtime backup schema')
    objects = db.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    allowed = TABLES | ({'runs', 'experiments'} if version >= 2 else set()) | ({'scenario_metadata'} if version >= 3 else set()) | ({'checkpoint_metadata'} if version >= 4 else set())
    if ({name for kind, name in objects if kind == 'table'} != allowed
            or any(kind in ('trigger', 'view') for kind, name in objects)):
        raise ValueError('unexpected runtime backup schema objects')
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('runtime backup integrity failed')
    for table, limit in [('sessions', 100), ('scenarios', 100), ('checkpoints', 200)]:
        if db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] > limit:
            raise ValueError('runtime backup exceeds capacity')
    for owner, sid, payload in db.execute('SELECT owner,id,payload FROM scenarios'):
        scenario = Scenario.model_validate_json(payload)
        if scenario.scenario_id != sid or scenario != build_scenario(scenario.config):
            raise ValueError('runtime backup scenario mismatch')
    for sid, payload, prefix, ancestry in db.execute('SELECT id,payload,prefix,ancestry FROM sessions'):
        state = EngineState.model_validate_json(payload)
        restore_state({'engine_version': state.engine_version, 'schema_version': state.schema_version,
                       'state': state.model_dump(mode='json'), 'state_hash': digest(state)})
        manifest = ExperimentManifest(session_id=sid, scenario=state.scenario, ancestry=json.loads(ancestry),
            implementation_hash=implementation_hash(), operations=records(db, sid, json.loads(prefix)),
            interventions=state.interventions, event_hashes=[digest(e) for e in state.events],
            state_hash=digest(state), event_hash=digest(state.events))
        if not verify_manifest(manifest).verified:
            raise ValueError('runtime backup replay failed')
        events = [json.loads(r[0]) for r in db.execute(
            'SELECT payload FROM runtime_events WHERE session_id=? AND cursor>0 ORDER BY cursor', (sid,))]
        if canonical(events) != canonical(state.events):
            raise ValueError('runtime backup event mismatch')
    for payload, in db.execute('SELECT payload FROM checkpoints'):
        restore_state(json.loads(payload))
    if version >= 4:
        count = db.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0]
        if (db.execute('SELECT COUNT(*) FROM checkpoint_metadata').fetchone()[0] != count
                or db.execute('SELECT COUNT(*) FROM checkpoints c JOIN checkpoint_metadata m ON c.id=m.id').fetchone()[0] != count):
            raise ValueError('runtime backup checkpoint metadata mismatch')
        for created, in db.execute('SELECT created_at_utc FROM checkpoint_metadata'):
            CheckpointMetadata(created_at_utc=created)
    if version >= 3:
        if db.execute('SELECT COUNT(*) FROM scenario_metadata').fetchone()[0] != db.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0]:
            raise ValueError('runtime backup scenario metadata mismatch')
        for payload, created in db.execute('''SELECT s.payload,m.created_at_utc FROM scenarios s
            JOIN scenario_metadata m ON s.owner=m.owner AND s.id=m.id'''):
            ScenarioArchive(scenario=Scenario.model_validate_json(payload), created_at_utc=created)
    if version >= 2:
        for table, model, limit in [('runs', Run, 100), ('experiments', Experiment, 10)]:
            if db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] > limit:
                raise ValueError('runtime control backup exceeds capacity')
            for payload, in db.execute(f'SELECT payload FROM {table}'):
                model.model_validate_json(payload)
    return {'schema_version': version, 'sessions': db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]}


def copy_database(source: Path, destination: Path, expected_sha256: str | None = None) -> dict:
    source, destination = source.resolve(), destination.resolve()
    if not source.is_file() or source == destination:
        raise ValueError('source must exist; destination must be a different new file')
    if expected_sha256 is not None and sha256_file(source) != expected_sha256:
        raise ValueError('runtime backup checksum mismatch')
    db = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=10)
    created = False
    try:
        db.execute('BEGIN')
        validate_database(db)
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        created = True
        target = sqlite3.connect(destination)
        try:
            db.backup(target, pages=256, sleep=0.05)
            result = validate_database(target)
        finally:
            target.close()
        return {**result, 'sha256': sha256_file(destination)}
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['backup', 'restore'])
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--sha256')
    args = parser.parse_args()
    if args.operation == 'restore' and not args.sha256:
        parser.error('restore requires the original backup SHA-256')
    try:
        print(json.dumps(copy_database(args.source, args.destination, args.sha256), sort_keys=True))
    except (ValueError, OSError, sqlite3.Error, EngineError) as error:
        parser.exit(1, f'Runtime backup rejected: {type(error).__name__}\n')


if __name__ == '__main__':
    main()
