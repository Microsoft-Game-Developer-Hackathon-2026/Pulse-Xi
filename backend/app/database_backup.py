"""Trusted offline CLI support. Never exposed as a web upload/download endpoint."""
import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from .models import Match, MatchEvent


def sha256_file(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_database(db: sqlite3.Connection) -> dict:
    db.execute('PRAGMA trusted_schema=OFF')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version not in (1, 2, 3):
        raise ValueError('unsupported backup schema version')
    lifecycle_tables = {'package_metadata', 'match_lifecycle', 'deleted_matches'}
    studio_tables = {'director_studio_state', 'director_studio_approvals', 'director_studio_audit'}
    allowed = {'matches', 'events'} | lifecycle_tables | studio_tables
    schema = db.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    if any(kind in ('view','trigger') or kind == 'table' and name not in allowed for kind,name in schema):
        raise ValueError('backup contains unexpected schema objects')
    tables = {name for kind,name in schema if kind == 'table'}
    required = {'matches', 'events'}
    if version >= 2:
        required |= lifecycle_tables
    if version == 3:
        required |= studio_tables
    if not required <= tables:
        raise ValueError('backup is missing required tables')
    present_studio = tables & studio_tables
    if present_studio and present_studio != studio_tables:
        raise ValueError('backup contains an incomplete Director Studio schema')
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('backup failed database integrity checks')
    counts = {table:db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ('matches','events')}
    if counts['matches'] > 100 or db.execute('SELECT match_id FROM events GROUP BY match_id HAVING COUNT(*) > 1000').fetchone():
        raise ValueError('backup exceeds supported dataset capacity')
    matches: dict[str, Match] = {}
    for mid,payload in db.execute('SELECT match_id,payload FROM matches'):
        match = Match.model_validate_json(payload)
        if match.match_id != mid:
            raise ValueError('backup match identity mismatch')
        matches[mid] = match
    events_by_match: dict[str, list[MatchEvent]] = {}
    for mid,eid,seq,second,payload in db.execute('SELECT match_id,event_id,sequence,match_second,payload FROM events'):
        event = MatchEvent.model_validate_json(payload)
        if (event.match_id,event.event_id,event.sequence,event.match_second) != (mid,eid,seq,second):
            raise ValueError('backup event identity mismatch')
        events_by_match.setdefault(mid, []).append(event)
    if version >= 2:
        if db.execute('SELECT match_id FROM matches EXCEPT SELECT match_id FROM match_lifecycle').fetchone():
            raise ValueError('backup has missing lifecycle identities')
        if db.execute('SELECT match_id FROM matches INTERSECT SELECT match_id FROM deleted_matches').fetchone():
            raise ValueError('backup contains simultaneously live and deleted identities')
    if present_studio:
        _validate_studio(db, matches, events_by_match, require_actor=version == 3)
    return {'schema_version':version, **counts}


def _validate_studio(db: sqlite3.Connection, matches: dict[str, Match],
                     events_by_match: dict[str, list[MatchEvent]], *, require_actor: bool) -> None:
    """Validate Studio rows as versioned source-backed records before backup/restore."""
    from .director_studio import CueEdit, DraftUpdate, _materialize, _sources

    expected_columns = {
        'director_studio_state': {'match_id', 'revision', 'cues_json'},
        'director_studio_approvals': {'match_id', 'revision', 'snapshot_json', 'approved_at'},
        'director_studio_audit': {'id', 'match_id', 'revision', 'action', 'at_utc', 'actor'},
    }
    for table, expected in expected_columns.items():
        columns = {row[1] for row in db.execute(f'PRAGMA table_info({table})')}
        if table == 'director_studio_audit' and not require_actor:
            expected = expected - {'actor'}
            if 'actor' in columns:
                expected |= {'actor'}
        if columns != expected:
            raise ValueError(f'backup contains an unsupported {table} schema')

    states: dict[str, tuple[int, list[CueEdit]]] = {}
    for mid, revision, cues_json in db.execute(
            'SELECT match_id,revision,cues_json FROM director_studio_state'):
        if mid not in matches or type(revision) is not int or revision < 1:
            raise ValueError('backup contains an invalid Director Studio revision')
        try:
            raw = json.loads(cues_json)
            update = DraftUpdate.model_validate({'expected_revision': revision - 1, 'cues': raw})
            if mid in matches:
                _materialize(matches[mid], _sources(matches[mid], events_by_match.get(mid, [])), update.cues)
        except Exception as error:
            raise ValueError('backup contains an invalid Director Studio draft') from error
        states[mid] = (revision, update.cues)

    for mid, revision, snapshot_json, approved_at in db.execute(
            'SELECT match_id,revision,snapshot_json,approved_at FROM director_studio_approvals'):
        state = states.get(mid)
        if (mid not in matches or type(revision) is not int or state is None or revision < 1 or revision > state[0]
                or not isinstance(approved_at, str) or not approved_at):
            raise ValueError('backup contains an invalid approved Director Studio revision')
        try:
            snapshot = json.loads(snapshot_json)
            if (snapshot.get('schema_version') != 'director-studio-export/1'
                    or snapshot.get('match_id') != mid or snapshot.get('revision') != revision
                    or not isinstance(snapshot.get('cues'), list)):
                raise ValueError('invalid snapshot identity')
            edits = [CueEdit.model_validate({key: cue[key] for key in (
                'cue_id', 'order', 'start_match_second', 'show_duration_seconds', 'priority',
                'visual_template', 'safe_area', 'transition')}) for cue in snapshot['cues']]
            if mid in matches:
                expected = _materialize(matches[mid], _sources(matches[mid], events_by_match.get(mid, [])), edits)
                if expected != snapshot['cues']:
                    raise ValueError('snapshot cue differs from verified source')
            datetime.fromisoformat(approved_at.replace('Z', '+00:00'))
        except Exception as error:
            raise ValueError('backup contains an invalid Director Studio approval snapshot') from error

    actor_column = 'actor' if 'actor' in {row[1] for row in db.execute('PRAGMA table_info(director_studio_audit)')} else "'local_admin'"
    for mid, revision, action, at_utc, actor in db.execute(
            f'SELECT match_id,revision,action,at_utc,{actor_column} FROM director_studio_audit'):
        state = states.get(mid)
        if (mid not in matches or type(revision) is not int or state is None or not 1 <= revision <= state[0]
                or action not in {'draft_saved', 'approved'}
                or actor not in {'local_admin', 'producer_token'}):
            raise ValueError('backup contains an invalid Director Studio audit row')
        try:
            datetime.fromisoformat(at_utc.replace('Z', '+00:00'))
        except (AttributeError, ValueError) as error:
            raise ValueError('backup contains an invalid Director Studio audit timestamp') from error


def copy_database(source: Path, destination: Path, expected_sha256: str | None = None) -> dict:
    """SQLite online backup API, exclusive destination, verified before success.

    Restore callers supply the physical SHA-256 recorded by the backup command.
    Existing files are never overwritten; point the stopped app to a new verified file.
    """
    source, destination = source.resolve(), destination.resolve()
    if not source.is_file() or source == destination:
        raise ValueError('source must exist and destination must be a different new file')
    if expected_sha256 is not None and sha256_file(source) != expected_sha256:
        raise ValueError('backup checksum mismatch')
    connection = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=10)
    created = False
    try:
        connection.execute('BEGIN')
        validate_database(connection)
        # O_EXCL protects against a check/create race and accidental overwrite.
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        created = True
        target = sqlite3.connect(destination)
        try:
            connection.backup(target, pages=256, sleep=0.05)
            result = validate_database(target)
            if expected_sha256 is not None and result['schema_version'] == 2:
                # Restoring an older file must not reactivate confirmations from
                # before the restore. These are admin identities, not event IDs.
                with target:
                    for (mid,) in target.execute('SELECT match_id FROM match_lifecycle').fetchall():
                        target.execute('UPDATE match_lifecycle SET generation=? WHERE match_id=?',(uuid4().hex,mid))
                    for (mid,) in target.execute('SELECT match_id FROM deleted_matches').fetchall():
                        target.execute('UPDATE deleted_matches SET deletion_id=? WHERE match_id=?',(uuid4().hex,mid))
                result = validate_database(target)
        finally:
            target.close()
        return {**result, 'source':str(source), 'destination':str(destination), 'sha256':sha256_file(destination)}
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    finally:
        connection.close()
