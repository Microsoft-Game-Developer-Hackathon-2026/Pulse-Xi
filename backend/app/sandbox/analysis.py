"""Owner-scoped adapters to existing read-only recorded-event analysis.

The engine owns state, coordinates and canonicalization. These adapters never
advance a runtime, publish its events to the public match library or serialize it.
"""
from typing import Callable, Literal
from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from . import storage
from .engine import EngineError, match_record, match_events
from .models import RuntimeView
from .native_analysis import NativeEvent, NativeAnalysis, NativeEvidence, project, analyze
from ..models import Match, MatchEvent, MatchMetrics, EventType, Insight, ControlChaosResponse
from ..analytics import metrics_at, control_chaos_at
from ..pass_difficulty import (PassDifficulty, PassDifficultyPage, PassDifficultyEvidence,
                               score_pass, verify_pass_difficulty)
from ..exports import analysis_export
from ..evidence import insights_for, verify_control_turning_point


class RecordedAnalysis(BaseModel):
    schema_version: Literal['runtime-analysis/1'] = 'runtime-analysis/1'
    session_id: str
    scenario_id: str
    revision: int
    authoritative_tick: int
    event_cursor: int
    state_hash: str
    event_hash: str
    at_second: int
    match: Match
    events: list[MatchEvent]
    metrics: MatchMetrics
    insights: list[Insight]


class RuntimeControlChaos(BaseModel):
    schema_version: Literal['runtime-control-chaos/1'] = 'runtime-control-chaos/1'
    session_id: str
    branch_id: str
    scenario_id: str
    revision: int
    authoritative_tick: int
    event_cursor: int
    at_second: int
    duration_seconds: int
    halftime_tick: int
    state_hash: str
    event_hash: str
    hash_scope: str
    current_window_complete: bool
    comparison_available: bool
    analysis: ControlChaosResponse


Projection = Literal['legacy', 'native']


def source(owner: str, session_id: str, cutoff: int, projection: Projection = 'legacy'):
    view = storage.get_runtime(owner, session_id)
    if cutoff > view.tick:
        raise EngineError('future_analysis_cutoff', 422)
    if projection == 'native':
        match, projected = project(view)
    else:
        match, projected = match_record(view.state, session_id), match_events(view.state, session_id)
    events = [e for e in projected if e.match_second <= cutoff]
    return view, match, events


def register(router: APIRouter, operator: Callable[..., str]) -> None:
    def private_response(response: Response) -> None:
        response.headers['Cache-Control'] = 'no-store'


    @router.get('/sessions/{session_id}/analysis', response_model=RecordedAnalysis | NativeAnalysis, dependencies=[Depends(private_response)])
    def recorded_analysis(session_id: str, at_second: int = Query(ge=0, le=5400), projection: Projection = 'legacy', owner: str = Depends(operator)):
        view, match, events = source(owner, session_id, at_second, projection)
        if projection == 'native':
            return analyze(view, match, events, at_second)
        return RecordedAnalysis(session_id=session_id, scenario_id=view.scenario_id,
            revision=view.revision, authoritative_tick=view.tick, event_cursor=view.event_cursor,
            state_hash=view.state_hash, event_hash=view.event_hash, at_second=at_second,
            match=match, events=events, metrics=metrics_at(match, events, at_second), insights=insights_for(match, events, at_second))

    @router.get('/sessions/{session_id}/control-chaos', response_model=RuntimeControlChaos, dependencies=[Depends(private_response)])
    def runtime_control(session_id: str, at_second: int = Query(ge=0, le=5400),
                        window_seconds: int = Query(300, ge=300, le=900), owner: str = Depends(operator)):
        if window_seconds not in (300, 600, 900):
            raise EngineError('unsupported_control_window', 422)
        # One owner-scoped captured view supplies events, revision and hashes.
        view, match, events = source(owner, session_id, at_second, 'native')
        packet = control_chaos_at(match, events, at_second, window_seconds)
        if any(not verify_control_turning_point(claim, match, events, at_second, window_seconds)
               for claim in packet.interpretation.turning_points):
            raise EngineError('control_evidence_verification_failed', 500)
        return {
            'schema_version': 'runtime-control-chaos/1',
            'session_id': session_id, 'branch_id': session_id, 'scenario_id': view.scenario_id,
            'revision': view.revision, 'authoritative_tick': view.tick, 'event_cursor': view.event_cursor,
            'at_second': at_second, 'duration_seconds': match.duration_seconds,
            'halftime_tick': match.halftime_tick,
            'state_hash': view.state_hash, 'event_hash': view.event_hash,
            'hash_scope': 'captured authoritative boundary, not rewound inspection cutoff',
            'current_window_complete': at_second >= window_seconds,
            'comparison_available': packet.previous_window is not None,
            'analysis': packet,
        }

    @router.get('/sessions/{session_id}/pass-difficulty', response_model=PassDifficultyPage, dependencies=[Depends(private_response)])
    def difficulties(session_id: str, at_second: int = Query(ge=0, le=5400),
                     cursor: int = Query(0, ge=0, le=20000), limit: int = Query(200, ge=1, le=200), projection: Projection = 'legacy', owner: str = Depends(operator)):
        _, match, events = source(owner, session_id, at_second, projection)
        passes = [e for e in events if e.event_type == EventType.pass_]
        page = [e for e in passes if e.sequence > cursor][:limit]
        return PassDifficultyPage(match_id=session_id, at_second=at_second,
            items=[score_pass(match, e, at_second) for e in page],
            next_cursor=page[-1].sequence if page and any(e.sequence > page[-1].sequence for e in passes) else None,
            total_visible_passes=len(passes))

    @router.get('/sessions/{session_id}/passes/{event_id}/difficulty/evidence', response_model=PassDifficultyEvidence | NativeEvidence, dependencies=[Depends(private_response)])
    def evidence(session_id: str, event_id: str, at_second: int = Query(ge=0, le=5400), projection: Projection = 'legacy', owner: str = Depends(operator)):
        _, match, events = source(owner, session_id, at_second, projection)
        event = next((e for e in events if e.event_id == event_id and e.event_type == EventType.pass_), None)
        if event is None:
            raise EngineError('visible_pass_not_found', 404)
        claim = score_pass(match, event, at_second)
        envelope = NativeEvidence if projection == 'native' else PassDifficultyEvidence
        return envelope(claim=claim, verified=verify_pass_difficulty(claim, match, events),
            source_events=[e for e in events if e.event_id in claim.supporting_event_ids])

    @router.get('/sessions/{session_id}/passes/{event_id}/difficulty', response_model=PassDifficulty, dependencies=[Depends(private_response)])
    def difficulty(session_id: str, event_id: str, at_second: int = Query(ge=0, le=5400), projection: Projection = 'legacy', owner: str = Depends(operator)):
        return evidence(session_id, event_id, at_second, projection, owner).claim

    @router.get('/sessions/{session_id}/analysis-export')
    def export(session_id: str, at_second: int = Query(ge=0, le=5400),
               category: Literal['events', 'pass', 'metrics'] = 'events', format: Literal['json', 'csv'] = 'json',
               team_id: str | None = Query(None, max_length=160), event_type: EventType | None = None,
               event_id: str | None = Query(None, max_length=160), projection: Projection = 'legacy', owner: str = Depends(operator)):
        view, match, events = source(owner, session_id, at_second, projection)
        return analysis_export(match, events, at_second, category, format, team_id, event_type, event_id,
            event_fields=list(NativeEvent.model_fields) if projection == 'native' else None,
            runtime_provenance={**({'analysis_projection':'runtime-native-analysis/1', 'duration_seconds':match.duration_seconds,
                'halftime_tick':match.halftime_tick} if projection == 'native' else {}), 'session_id': session_id, 'scenario_id': view.scenario_id,
                'revision': view.revision, 'authoritative_tick': view.tick, 'event_cursor': view.event_cursor,
                'state_hash': view.state_hash, 'event_hash': view.event_hash,
                'engine_version': view.state.engine_version, 'scenario_seed': view.state.scenario.config.seed,
                'boundary_scope': 'hashes identify the captured runtime boundary, not a rewound state at cutoff'})
