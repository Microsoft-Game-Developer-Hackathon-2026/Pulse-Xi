"""Trusted offline CLI support. Never exposed as a web upload/download endpoint."""
import hashlib
import os
import sqlite3
from pathlib import Path
from uuid import uuid4
from .models import Match, MatchEvent


def sha256_file(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_database(db: sqlite3.Connection) -> dict:
    db.execute('PRAGMA trusted_schema=OFF')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version not in (1,2):
        raise ValueError('unsupported backup schema version')
    allowed = {'matches','events','package_metadata','match_lifecycle','deleted_matches'}
    schema = db.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    if any(kind in ('view','trigger') or kind == 'table' and name not in allowed for kind,name in schema):
        raise ValueError('backup contains unexpected schema objects')
    tables = {name for kind,name in schema if kind == 'table'}
    required = {'matches','events'} | ({'match_lifecycle','deleted_matches','package_metadata'} if version == 2 else set())
    if not required <= tables:
        raise ValueError('backup is missing required tables')
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('backup failed database integrity checks')
    counts = {table:db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ('matches','events')}
    if counts['matches'] > 100 or db.execute('SELECT match_id FROM events GROUP BY match_id HAVING COUNT(*) > 1000').fetchone():
        raise ValueError('backup exceeds supported dataset capacity')
    for mid,payload in db.execute('SELECT match_id,payload FROM matches'):
        if Match.model_validate_json(payload).match_id != mid:
            raise ValueError('backup match identity mismatch')
    for mid,eid,seq,second,payload in db.execute('SELECT match_id,event_id,sequence,match_second,payload FROM events'):
        event = MatchEvent.model_validate_json(payload)
        if (event.match_id,event.event_id,event.sequence,event.match_second) != (mid,eid,seq,second):
            raise ValueError('backup event identity mismatch')
    if version == 2:
        if db.execute('SELECT match_id FROM matches EXCEPT SELECT match_id FROM match_lifecycle').fetchone():
            raise ValueError('backup has missing lifecycle identities')
        if db.execute('SELECT match_id FROM matches INTERSECT SELECT match_id FROM deleted_matches').fetchone():
            raise ValueError('backup contains simultaneously live and deleted identities')
    return {'schema_version':version, **counts}


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
