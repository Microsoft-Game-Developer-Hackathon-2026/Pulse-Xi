"""Authenticated operator API. No anonymous runtime state or mutation routes."""
import json
import os
import secrets
import sqlite3
import asyncio

from fastapi import APIRouter, Depends, Header, Query, Response, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from pydantic import ValidationError, Field
from typing import Literal

from . import storage
from .engine import EngineError, build_scenario, capture_state, match_events, match_record, presets, implementation_hash, parse_json
from .manifest import verify_manifest
from .prooftrail import SandboxInsight, build_sandbox_insight
from .models import (AuditEntry, CheckpointView, Command, CreateSession, EventPage, ExperimentManifest,
                     MutationResult, RestoreRequest, RuntimeView, Scenario, ScenarioConfig, Snapshot,
                     Verification, ErrorResponse, Model, ENGINE_VERSION, SCHEMA_VERSION, RNG_ALGORITHM)
from ..models import Match, MatchEvent
from .control import (Run, RunRequest, Experiment, ExperimentRequest, create_run, create_experiment,
                      cancel_run, cancel_experiment, read, list_runs, list_experiments)
from .experiments import Comparison, ExperimentBundle, comparison, bundle, verify_bundle
from .scenario_archive import ScenarioArchive, ScenarioSummary


class SessionSummary(Model):
    session_id: str
    scenario_id: str
    tick: int = Field(ge=0, le=5400)
    revision: int = Field(ge=0, le=2048)
    event_cursor: int = Field(ge=1, le=20000)
    lifecycle: Literal['paused', 'running', 'completed', 'cancelled']


class CheckpointSummary(Model):
    checkpoint_id: str
    session_id: str
    scenario_id: str
    tick: int
    revision: int
    event_cursor: int
    state_hash: str


class HistoricalView(Model):
    session_id: str
    source_revision: int
    at_tick: int
    read_only: Literal[True]
    snapshot: Snapshot


class VersionInfo(Model):
    engine_version: str
    schema_version: str
    rng_algorithm: str
    implementation_hash: str
    tick_seconds: int
    max_command_ticks: int
    driver: str
    limits: dict[str, int]


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
            except json.JSONDecodeError:
                return JSONResponse({'detail': {'code': 'corrupt_snapshot'}}, status_code=422)
            except RuntimeError:
                return JSONResponse({'detail': {'code': 'runtime_database_unavailable'}}, status_code=503)
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


@router.get('/versions', response_model=VersionInfo)
def versions(owner: str = Depends(require_operator)):
    return {'engine_version': ENGINE_VERSION, 'schema_version': SCHEMA_VERSION, 'rng_algorithm': RNG_ALGORITHM,
            'implementation_hash': implementation_hash(),
            'tick_seconds': 1, 'max_command_ticks': 300, 'driver': 'durable-server-and-explicit-commands',
            'limits': {'scenarios': 100, 'sessions': 100, 'checkpoints': 200, 'commands_per_session': 2048,
                       'audit_entries_per_session': 4096, 'pending_actions': 128, 'ancestry_depth': 32,
                       'runs': 100, 'experiments': 10, 'paired_trials': 5, 'trial_horizon': 600}}


@router.get('/presets', response_model=dict[str, ScenarioConfig])
def get_presets(owner: str = Depends(require_operator)):
    return presets()


@router.post('/scenarios', response_model=Scenario)
def create_scenario(config: ScenarioConfig, owner: str = Depends(require_operator)):
    return storage.save_scenario(owner, build_scenario(config))


def private_scenario_response(response: Response):
    response.headers['Cache-Control'] = 'no-store'


@router.get('/scenarios', response_model=list[ScenarioSummary], dependencies=[Depends(private_scenario_response)])
def scenarios(owner: str = Depends(require_operator)):
    """At most 100 owned scenario summaries, ordered by content-derived ID."""
    return storage.list_scenarios(owner)


@router.post('/scenarios/import', response_model=ScenarioArchive, dependencies=[Depends(private_scenario_response)],
             responses={400: {'description': 'Ambiguous, nonfinite or excessively nested JSON'},
                        413: {'description': 'Request body exceeds 2,000,000 bytes'}})
def import_scenario(request: ScenarioArchive | ScenarioConfig, owner: str = Depends(require_operator)):
    if isinstance(request, ScenarioConfig):
        scenario = storage.save_scenario(owner, build_scenario(request))
        return storage.get_scenario_archive(owner, scenario.scenario_id)
    return storage.import_scenario(owner, request)


@router.get('/scenarios/{scenario_id}/archive', response_model=ScenarioArchive, dependencies=[Depends(private_scenario_response)])
def scenario_archive(scenario_id: str, owner: str = Depends(require_operator)):
    return storage.get_scenario_archive(owner, scenario_id)


@router.get('/scenarios/{scenario_id}', response_model=Scenario)
def get_scenario(scenario_id: str, owner: str = Depends(require_operator)):
    return storage.get_scenario(owner, scenario_id)


@router.post('/sessions', response_model=MutationResult)
def create_session(request: CreateSession, owner: str = Depends(require_operator)):
    return storage.create_session(owner, request.operation_id, request.scenario_id)


@router.get('/sessions', response_model=list[SessionSummary])
def sessions(owner: str = Depends(require_operator)):
    return storage.list_sessions(owner)


@router.get('/sessions/{session_id}/state', response_model=RuntimeView)
def state(session_id: str, owner: str = Depends(require_operator)):
    return storage.get_runtime(owner, session_id)


@router.get('/sessions/{session_id}/snapshot', response_model=Snapshot)
def snapshot(session_id: str, owner: str = Depends(require_operator)):
    return capture_state(storage.get_runtime(owner, session_id).state)


@router.get('/sessions/{session_id}/history', response_model=HistoricalView)
def history(session_id: str, at_tick: int = Query(ge=0, le=5400), owner: str = Depends(require_operator)):
    return storage.history_at(owner, session_id, at_tick)


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


@router.get('/sessions/{branch_session_id}/prooftrail', response_model=SandboxInsight)
def prooftrail(branch_session_id: str, baseline_session_id: str = Query(min_length=1, max_length=100),
               intervention_id: str = Query(min_length=1, max_length=80),
               at_tick: int = Query(ge=0, le=5400), owner: str = Depends(require_operator)):
    """Compare one verified checkpoint descendant with its baseline for the same owner."""
    branch = storage.get_runtime(owner, branch_session_id)
    baseline = storage.get_runtime(owner, baseline_session_id)
    branch_manifest = storage.manifest(owner, branch_session_id)
    baseline_manifest = storage.manifest(owner, baseline_session_id)
    ancestor = next((item for item in branch_manifest.ancestry
                     if item.session_id == baseline_session_id), None)
    if ancestor is None:
        raise EngineError('baseline_not_ancestor', 422)
    checkpoint = storage.get_checkpoint(owner, ancestor.checkpoint_id)
    if checkpoint.session_id != baseline_session_id or checkpoint.snapshot.state_hash != ancestor.snapshot_hash:
        raise EngineError('checkpoint_mismatch', 409)
    return build_sandbox_insight(branch, baseline, branch_manifest, baseline_manifest,
                                 intervention_id, at_tick, checkpoint.tick)

@router.get('/sessions/{session_id}/checkpoints', response_model=list[CheckpointSummary])
def checkpoints(session_id: str, owner: str = Depends(require_operator)):
    return storage.list_checkpoints(owner, session_id)


@router.post('/sessions/{session_id}/runs', response_model=Run)
def run(session_id: str, request: RunRequest, owner: str = Depends(require_operator)):
    return create_run(owner, session_id, request)


@router.get('/sessions/{session_id}/runs', response_model=list[Run])
def session_runs(session_id: str, owner: str = Depends(require_operator)):
    return list_runs(owner, session_id)


@router.get('/runs/{run_id}', response_model=Run)
def run_state(run_id: str, owner: str = Depends(require_operator)):
    return read('runs', owner, run_id)[1]


@router.post('/runs/{run_id}/cancel', response_model=Run)
def stop_run(run_id: str, owner: str = Depends(require_operator)):
    return cancel_run(owner, run_id)


@router.post('/experiments', response_model=Experiment)
def experiment(request: ExperimentRequest, owner: str = Depends(require_operator)):
    return create_experiment(owner, request)


@router.get('/experiments', response_model=list[Experiment])
def experiments(owner: str = Depends(require_operator)):
    return list_experiments(owner)


@router.post('/experiments/verify', response_model=Verification)
def verify_experiment(request: ExperimentBundle, owner: str = Depends(require_operator)):
    return verify_bundle(request)


@router.get('/experiments/{experiment_id}', response_model=Experiment)
def experiment_state(experiment_id: str, owner: str = Depends(require_operator)):
    return read('experiments', owner, experiment_id)[1]


@router.post('/experiments/{experiment_id}/cancel', response_model=Experiment)
def stop_experiment(experiment_id: str, owner: str = Depends(require_operator)):
    return cancel_experiment(owner, experiment_id)


@router.get('/experiments/{experiment_id}/comparison', response_model=Comparison)
def experiment_comparison(experiment_id: str, owner: str = Depends(require_operator)):
    return comparison(owner, experiment_id)


@router.get('/experiments/{experiment_id}/manifest', response_model=ExperimentBundle)
def experiment_manifest(experiment_id: str, owner: str = Depends(require_operator)):
    return bundle(owner, experiment_id)


@router.websocket('/sessions/{session_id}/observe')
async def observe(websocket: WebSocket, session_id: str, cursor: int = Query(default=0, ge=0, le=20000)):
    # Authenticate via a first frame, never URL/query/localStorage credentials.
    origin = websocket.headers.get('origin')
    allowed = {'http://localhost:5173', 'http://127.0.0.1:5173',
               ('https://' if websocket.url.scheme == 'wss' else 'http://') + websocket.url.netloc}
    if origin and origin not in allowed:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=5)
        if len(raw) > 4096:
            raise EngineError('unauthorized', 403)
        frame = parse_json(raw)
        if not isinstance(frame, dict) or set(frame) != {'token'} or not isinstance(frame['token'], str):
            raise EngineError('unauthorized', 403)
        owner = require_operator('Bearer ' + frame['token'])
        last_revision = -1
        while True:
            # Revalidate rotated/revoked credentials before every observation.
            if require_operator('Bearer ' + frame['token']) != owner:
                raise EngineError('unauthorized', 403)
            view = await run_in_threadpool(storage.get_runtime, owner, session_id)
            if cursor > view.event_cursor:
                raise EngineError('cursor_ahead')
            if last_revision == -1:
                await websocket.send_json({'kind': 'snapshot', 'view': view.model_dump(mode='json')})
            elif view.revision != last_revision:
                value = view.model_dump(mode='json')
                events = value['state'].pop('events')
                await websocket.send_json({'kind': 'delta', 'view': value, 'from_cursor': cursor, 'events': events[cursor:]})
            cursor, last_revision = view.event_cursor, view.revision
            # Receive disconnects promptly, without requiring a simulation change.
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=0.25)
                if message['type'] == 'websocket.disconnect':
                    return
                if message.get('text') != 'ping':
                    await websocket.close(code=1008)
                    return
            except TimeoutError:
                pass
    except (WebSocketDisconnect, RuntimeError):
        return
    except (EngineError, ValueError, TimeoutError, KeyError, TypeError) as error:
        await websocket.close(code=4400 + min(getattr(error, 'status', 400) % 100, 99))


# Existing analysis services consume only authenticated, committed engine events.
from .analysis import register as register_analysis
register_analysis(router, require_operator)

