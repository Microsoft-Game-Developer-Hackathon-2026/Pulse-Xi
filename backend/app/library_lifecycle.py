"""Administrative dataset lifecycle; not simulation checkpoints."""
import ipaddress
import os
import secrets
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .data_hub import require_import_token
from .storage import StorageConflict, connect, database_path
import sqlite3
import json
from .models import Match
from .data_hub import quality


def local_admin_enabled(request: Request) -> bool:
    if os.getenv('PULSE_ENABLE_LOCAL_DATA_ADMIN') != '1' or not request.client:
        return False
    if any(key.lower() in ('forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-real-ip') for key in request.headers):
        return False
    try:
        host = request.url.hostname
        local_host = host == 'localhost' or host is not None and ipaddress.ip_address(host).is_loopback
        return bool(local_host and ipaddress.ip_address(request.client.host).is_loopback)
    except ValueError:
        return False


def require_local_admin(request: Request, _: None = Depends(require_import_token)) -> None:
    if not local_admin_enabled(request):
        raise HTTPException(403, 'Dataset lifecycle is disabled. It requires explicit local administrator mode and a direct loopback connection; public/proxied administration is unsupported.')


def require_studio_producer(request: Request, authorization: str | None = Header(default=None)) -> str:
    """Authorize a configured shared-demo producer or an explicitly local admin."""
    from .deployment import deployment_mode

    if deployment_mode() == 'public-readonly':
        raise HTTPException(403, 'The public read-only deployment does not allow studio changes.')
    expected = os.getenv('PULSE_STUDIO_PRODUCER_TOKEN', '')
    if expected:
        if len(expected) < 32:
            raise HTTPException(503, 'Studio producer access is misconfigured; the token must contain at least 32 characters.')
        supplied = (authorization or '').removeprefix('Bearer ')
        if not (authorization or '').startswith('Bearer ') or not secrets.compare_digest(
                supplied.encode('utf-8'), expected.encode('utf-8')):
            raise HTTPException(403, 'Producer authorization required.')
        return 'producer_token'
    require_import_token(authorization)
    if not local_admin_enabled(request):
        raise HTTPException(403, 'Studio editing requires configured producer access or explicit local administrator mode.')
    return 'local_admin'


class LifecycleAction(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    action: Literal['archive', 'restore', 'delete']
    confirm_match_id: str = Field(min_length=1, max_length=160)
    generation: str = Field(pattern=r'^[0-9a-f]{32}$')
    revision: int = Field(ge=1)


def change_lifecycle(match_id: str, action: LifecycleAction) -> dict:
    if action.confirm_match_id != match_id:
        raise ValueError('confirmation must exactly match the selected match ID')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT generation,revision,archived FROM match_lifecycle WHERE match_id=?', (match_id,)).fetchone()
        if row is None:
            raise KeyError('imported match not found')
        if row[:2] != (action.generation, action.revision):
            raise StorageConflict('dataset changed; refresh the library and confirm the current revision')
        if action.action == 'delete':
            if db.execute('SELECT COUNT(*) FROM deleted_matches').fetchone()[0] >= 10_000:
                raise StorageConflict('deletion safety ledger is full; trusted offline maintenance is required')
            deletion_id = uuid4().hex
            db.execute('INSERT INTO deleted_matches VALUES (?,?,?)', (match_id, deletion_id, datetime.now(timezone.utc).isoformat()))
            # Studio records are tied to the imported match identity. Remove
            # them in the same transaction so recovery cannot inherit stale
            # cues or approvals from the deleted source.
            existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            tables = ('director_studio_approvals', 'director_studio_audit',
                      'director_studio_state', 'package_metadata', 'events',
                      'match_lifecycle', 'matches')
            for table in tables:
                if table in existing:
                    db.execute(f'DELETE FROM {table} WHERE match_id=?', (match_id,))
            return {'match_id':match_id, 'status':'deleted', 'deletion_id':deletion_id}
        archived = int(action.action == 'archive')
        if row[2] != archived:
            db.execute('UPDATE match_lifecycle SET archived=?, revision=revision+1 WHERE match_id=?', (archived, match_id))
        return {'match_id':match_id, 'status':'archived' if archived else 'active'}


def deletion_record(match_id: str) -> dict | None:
    path = database_path().resolve()
    if not path.is_file():
        return None
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='deleted_matches' AND type='table'").fetchone():
            return None
        row = db.execute('SELECT deletion_id,deleted_at FROM deleted_matches WHERE match_id=?', (match_id,)).fetchone()
        return {'deletion_id':row[0], 'deleted_at':row[1]} if row else None
    finally:
        db.close()


def library_entries() -> list[dict]:
    """Factual aggregates in one read snapshot; no full event deserialization."""
    with connect() as db:
        db.execute('BEGIN')
        rows = db.execute('''SELECT m.match_id,m.payload,l.generation,l.revision,l.archived,p.provenance
            FROM matches m LEFT JOIN match_lifecycle l USING(match_id)
            LEFT JOIN package_metadata p USING(match_id) ORDER BY m.match_id''').fetchall()
        totals = {r[0]: r[1:] for r in db.execute('''WITH ordered AS (
            SELECT *, LAG(match_second) OVER (PARTITION BY match_id ORDER BY sequence) AS previous_second FROM events)
            SELECT match_id,COUNT(*),MIN(match_second),MAX(match_second),
            SUM(json_extract(payload,'$.start') IS NULL),SUM(json_extract(payload,'$.end') IS NULL),
            SUM(json_extract(payload,'$.actor_id') IS NULL),
            SUM(json_extract(payload,'$.type')='pass' AND json_extract(payload,'$.recipient_id') IS NULL),
            SUM(json_extract(payload,'$.type')='pass'),
            SUM(json_extract(payload,'$.type')='pass' AND json_extract(payload,'$.start') IS NOT NULL AND json_extract(payload,'$.end') IS NOT NULL),
            SUM(previous_second > match_second) FROM ordered GROUP BY match_id''')}
        categories: dict[str, dict[str,int]] = {}
        for mid, kind, count in db.execute("SELECT match_id,json_extract(payload,'$.type'),COUNT(*) FROM events GROUP BY match_id,json_extract(payload,'$.type') ORDER BY match_id,2"):
            categories.setdefault(mid,{})[kind] = count
    result = []
    for mid, payload, generation, revision, archived, provenance in rows:
        match = Match.model_validate_json(payload)
        data = quality(match, [])
        if mid in totals:
            values = totals[mid]
            keys = ('event_count','first_second','last_second','missing_start','missing_end','missing_actor','missing_recipient_on_passes','pass_count','passes_with_coordinates')
            data.update(dict(zip(keys, values)))
            data['sequence_consistent'] = not values[-1]
            data['event_types'] = categories[mid]
        result.append({'match':match, 'origin':'imported', 'quality':data,
                       'provenance':json.loads(provenance) if provenance else None,
                       'lifecycle':{'generation':generation, 'revision':revision, 'archived':bool(archived)}})
    return result
