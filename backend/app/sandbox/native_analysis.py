"""Read-only native-period projection; never a serializer for engine checkpoints."""
from collections import Counter
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..analytics import metrics_at
from ..models import Match, MatchEvent, Team, Player, Point, MatchMetrics, Insight
from ..pass_difficulty import PassDifficulty
from .models import RuntimeView


class NativeMatch(Match):
    schema_version: Literal['runtime-match/1'] = 'runtime-match/1'
    event_source: Literal['authoritative-runtime'] = 'authoritative-runtime'
    duration_seconds: int = Field(ge=60, le=5400)
    halftime_tick: int


class NativeEvent(MatchEvent):
    """Reuse event fields, replacing only the legacy period/calendar contract."""
    model_config = ConfigDict(populate_by_name=True, extra='forbid', allow_inf_nan=False)
    schema_version: Literal['runtime-event/1'] = 'runtime-event/1'
    source_type: Literal['authoritative-runtime'] = 'authoritative-runtime'
    generated_at_utc: datetime | None = None
    tick: int = Field(ge=0, le=5400)
    duration_seconds: int = Field(ge=60, le=5400)
    halftime_tick: int

    @model_validator(mode='after')
    def check_period(self):
        # Override the inherited fixed-2700 validator, never the legacy class.
        if self.duration_seconds % 2 or self.halftime_tick != self.duration_seconds // 2:
            raise ValueError('invalid native period boundary')
        if self.tick != self.match_second or self.tick > self.duration_seconds:
            raise ValueError('invalid native event tick')
        # Halftime itself is emitted in period 1 before the engine switches to 2.
        if self.period == 1 and self.tick > self.halftime_tick:
            raise ValueError('first-period event after native halftime')
        if self.period == 2 and self.tick < self.halftime_tick:
            raise ValueError('second-period event before native halftime')
        return self


class NativeEvidence(BaseModel):
    schema_version: Literal['runtime-pass-evidence/1'] = 'runtime-pass-evidence/1'
    claim: PassDifficulty
    verified: bool
    source_events: list[NativeEvent]


class NativeClock(BaseModel):
    duration_seconds: int
    halftime_tick: int
    current_period: Literal[1, 2]
    inspection_period: Literal[1, 2]
    units: Literal['authoritative match seconds'] = 'authoritative match seconds'


class NativeAnalysis(BaseModel):
    schema_version: Literal['runtime-native-analysis/1'] = 'runtime-native-analysis/1'
    session_id: str
    branch_id: str
    scenario_id: str
    revision: int
    authoritative_tick: int
    event_cursor: int
    state_hash: str
    event_hash: str
    at_second: int
    clock: NativeClock
    match: NativeMatch
    events: list[NativeEvent]
    metrics: MatchMetrics
    score: dict[str, int]
    event_counts_by_team: dict[str, dict[str, int]]
    insights: list[Insight] = Field(default_factory=list)
    unavailable: dict[str, str]
    provenance: dict[str, str]


def project(view: RuntimeView) -> tuple[NativeMatch, list[NativeEvent]]:
    state, config = view.state, view.state.scenario.config
    teams = [Team(team_id=t.team_id, name=t.name, color=t.color, players=[
        Player(player_id=p.player_id, name=p.name, role=a.role, shirt_number=i)
        for i, (p, a) in enumerate(zip(t.players, [a for a in state.actors if a.team_id == t.team_id]), 1)
    ]) for t in (config.home, config.away)]
    duration = config.duration_seconds
    match = NativeMatch(match_id=view.session_id, title=f'{teams[0].name} vs {teams[1].name}',
                        seed=config.seed, home=teams[0], away=teams[1], duration_seconds=duration,
                        halftime_tick=duration // 2)
    events = [NativeEvent(event_id=f'{view.session_id}-{e.sequence}', match_id=view.session_id,
        sequence=e.sequence, tick=e.tick, match_second=e.tick, period=e.period,
        duration_seconds=duration, halftime_tick=duration // 2, team_id=e.team_id,
        actor_id=e.actor_id, recipient_id=e.recipient_id, type=e.type, outcome=e.outcome,
        start=Point(x=100-e.x if e.team_id == config.away.team_id else e.x, y=e.y),
        end=Point(x=100-e.end_x if e.team_id == config.away.team_id else e.end_x, y=e.end_y),
        possession_id=str(e.possession_id), qualifiers={'engine_version':state.engine_version,
            'scenario_id':view.scenario_id, 'session_id':view.session_id, 'policy_revision':e.policy_revision})
        for e in state.events]
    return match, events


def analyze(view: RuntimeView, match: NativeMatch, events: list[NativeEvent], cutoff: int) -> NativeAnalysis:
    metrics = metrics_at(match, events, cutoff)
    return NativeAnalysis(session_id=view.session_id, branch_id=view.session_id, scenario_id=view.scenario_id,
        revision=view.revision, authoritative_tick=view.tick, event_cursor=view.event_cursor,
        state_hash=view.state_hash, event_hash=view.event_hash, at_second=cutoff, match=match, events=events,
        clock=NativeClock(duration_seconds=match.duration_seconds, halftime_tick=match.halftime_tick,
            current_period=view.state.period, inspection_period=1 if cutoff < match.halftime_tick else 2),
        metrics=metrics, score={'home':metrics.home.goals, 'away':metrics.away.goals},
        event_counts_by_team={team.team_id:dict(Counter(e.event_type.value for e in events if e.team_id == team.team_id))
                             for team in (match.home, match.away)},
        unavailable={'legacy_insight_templates':'Legacy match-state/insight templates assume a fixed 2700-second halftime; native pass evidence remains available.',
            'continuous_tracking':'Only committed event observations exist, not continuous actor trajectories.',
            'event_wall_clock':'The engine supplies match ticks, not observed event calendar timestamps.'},
        provenance={'event_identity':'session_id + engine event sequence', 'coordinate_frame':'team attacking frame; away x mirrored from engine pitch',
            'hash_scope':'captured runtime boundary, not rewound state at inspection cutoff', 'engine_version':view.state.engine_version})
