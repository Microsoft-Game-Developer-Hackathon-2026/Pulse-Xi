"""Authenticated operator API. No anonymous runtime state or mutation routes."""
import json
import os
import secrets
import sqlite3

from fastapi import APIRouter, Depends, Header, Query
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import storage
from .engine import EngineError, build_scenario, capture_state, match_events, match_record, presets, implementation_hash
from .manifest import verify_manifest
from .models import (AuditEntry, CheckpointView, Command, CreateSession, EventPage, ExperimentManifest,
                     MutationResult, RestoreRequest, RuntimeView, Scenario, ScenarioConfig, Snapshot,
                     Verification, ErrorResponse, ENGINE_VERSION, SCHEMA_VERSION, RNG_ALGORITHM)
from ..models import Match, MatchEvent


class RuntimeRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            try:
                return await original(request)
            except EngineError as error:
                return JSONResponse({'detail': {'code': error.code}}, status_code=error.status)
            except sqlite3.Error:
                return JSONResponse({'detail': {'code': 'transaction_failed'}}, status_code=503)
            except ValidationError:
                return JSONResponse({'detail': {'code': 'corrupt_snapshot'}}, status_code=422)
        return handler


def require_operator(authorization: str | None = Header(default=None)) -> str:
    raw = os.getenv('PULSE_RUNTIME_TOKENS', '')
    try:
        tokens = json.loads(raw) if raw else {'operator': os.getenv('PULSE_RUNTIME_TOKEN', '')}
    except ValueError:
        raise EngineError('runtime_auth_unconfigured', 503) from None
    if (not isinstance(tokens, dict) or not tokens or len(tokens) > 100
            or any(not isinstance(k, str) or not k or len(k) > 80 or not isinstance(v, str)
                   or len(v) < 32 or not v.isascii() for k, v in tokens.items())
            or len(set(tokens.values())) != len(tokens)):
        raise EngineError('runtime_auth_unconfigured', 503)
    supplied = authorization.removeprefix('Bearer ') if authorization and authorization.startswith('Bearer ') else ''
    if not supplied.isascii():
        raise EngineError('unauthorized', 403)
    for owner, token in sorted(tokens.items()):
        if secrets.compare_digest(supplied, token):
            return owner
    raise EngineError('unauthorized', 403)


router = APIRouter(prefix='/api/sandbox', tags=['authoritative-runtime'], route_class=RuntimeRoute,
                   responses={status: {'model': ErrorResponse, 'description': description} for status, description in (
                       (403, 'Unauthorized operator'), (404, 'Unknown or inaccessible identity'),
                       (409, 'Revision, lifecycle, cursor or idempotency conflict'),
                       (429, 'Bounded resource limit'), (503, 'Auth unconfigured or transaction unavailable'))})


@router.get('/versions')
def versions(owner: str = Depends(require_operator)):
    return {'engine_version': ENGINE_VERSION, 'schema_version': SCHEMA_VERSION, 'rng_algorithm': RNG_ALGORITHM,
            'implementation_hash': implementation_hash(),
            'tick_seconds': 1, 'max_command_ticks': 300, 'driver': 'manual-bounded',
            'limits': {'scenarios': 100, 'sessions': 100, 'checkpoints': 200, 'commands_per_session': 2048,
                       'audit_entries_per_session': 4096, 'pending_actions': 128, 'ancestry_depth': 32}}


@router.get('/presets', response_model=dict[str, ScenarioConfig])
def get_presets(owner: str = Depends(require_operator)):
    return presets()


@router.post('/scenarios', response_model=Scenario)
def create_scenario(config: ScenarioConfig, owner: str = Depends(require_operator)):
    return storage.save_scenario(owner, build_scenario(config))


@router.get('/scenarios/{scenario_id}', response_model=Scenario)
def get_scenario(scenario_id: str, owner: str = Depends(require_operator)):
    return storage.get_scenario(owner, scenario_id)


@router.post('/sessions', response_model=MutationResult)
def create_session(request: CreateSession, owner: str = Depends(require_operator)):
    return storage.create_session(owner, request.operation_id, request.scenario_id)


@router.get('/sessions/{session_id}/state', response_model=RuntimeView)
def state(session_id: str, owner: str = Depends(require_operator)):
    return storage.get_runtime(owner, session_id)


@router.get('/sessions/{session_id}/snapshot', response_model=Snapshot)
def snapshot(session_id: str, owner: str = Depends(require_operator)):
    return capture_state(storage.get_runtime(owner, session_id).state)


@router.post('/sessions/{session_id}/commands', response_model=MutationResult)
def command(session_id: str, request: Command, owner: str = Depends(require_operator)):
    return storage.mutate(owner, session_id, request)


@router.get('/sessions/{session_id}/events', response_model=EventPage)
def events(session_id: str, cursor: int = Query(default=0, ge=0, le=20000),
           limit: int = Query(default=200, ge=1, le=1000), owner: str = Depends(require_operator)):
    return storage.read_events(owner, session_id, cursor, limit)


@router.get('/sessions/{session_id}/match-events', response_model=list[MatchEvent])
def compatible_events(session_id: str, cursor: int = Query(default=0, ge=0, le=20000),
                      limit: int = Query(default=200, ge=1, le=1000), owner: str = Depends(require_operator)):
    view = storage.get_runtime(owner, session_id)
    if cursor > view.event_cursor:
        raise EngineError('cursor_ahead')
    return match_events(view.state, session_id)[cursor:cursor + limit]


@router.get('/sessions/{session_id}/match', response_model=Match)
def compatible_match(session_id: str, owner: str = Depends(require_operator)):
    return match_record(storage.get_runtime(owner, session_id).state, session_id)


@router.get('/sessions/{session_id}/audit', response_model=list[AuditEntry])
def audit(session_id: str, owner: str = Depends(require_operator)):
    return storage.audit_log(owner, session_id)


@router.get('/checkpoints/{checkpoint_id}', response_model=CheckpointView)
def checkpoint(checkpoint_id: str, owner: str = Depends(require_operator)):
    return storage.get_checkpoint(owner, checkpoint_id)


@router.post('/checkpoints/{checkpoint_id}/restore', response_model=MutationResult)
def restore(checkpoint_id: str, request: RestoreRequest, owner: str = Depends(require_operator)):
    return storage.create_session(owner, request.operation_id, checkpoint_id=checkpoint_id,
                                  expected_revision=request.expected_revision)


@router.get('/sessions/{session_id}/manifest', response_model=ExperimentManifest)
def manifest(session_id: str, owner: str = Depends(require_operator)):
    return storage.manifest(owner, session_id)


@router.post('/verify', response_model=Verification)
def verify(manifest: ExperimentManifest, owner: str = Depends(require_operator)):
    return verify_manifest(manifest)
