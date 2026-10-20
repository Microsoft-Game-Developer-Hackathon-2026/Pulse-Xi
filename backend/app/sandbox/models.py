"""Versioned, bounded JSON contracts. All simulation arithmetic is integer-only."""
from typing import Annotated, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, model_validator

ENGINE_VERSION = 'zone-engine/1'
SCHEMA_VERSION = 'sandbox/1'
RNG_ALGORITHM = 'sha256-counter/1'
STREAMS = ('actor', 'decision', 'duel', 'finish')
Identifier = Annotated[str, Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')]
Digest = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
Percent = Annotated[int, Field(ge=0, le=100)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, validate_assignment=True)


class Tactics(Model):
    formation: Literal['4-3-3', '4-4-2', '3-5-2'] = '4-3-3'
    pressing: Percent = 50
    compactness: Percent = 50
    directness: Percent = 50
    tempo: Percent = 50
    risk: Percent = 50


class PlayerConfig(Model):
    player_id: Identifier
    name: str = Field(min_length=1, max_length=80)
    passing: Percent = 65
    finishing: Percent = 60
    defending: Percent = 60


class TeamConfig(Model):
    team_id: Identifier
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    players: list[PlayerConfig] = Field(min_length=11, max_length=11)
    tactics: Tactics = Field(default_factory=Tactics)


def team(side: str) -> TeamConfig:
    return TeamConfig(team_id=side, name='Northbridge FC' if side == 'home' else 'Harbor Athletic',
                      color='#3377ff' if side == 'home' else '#ff7733',
                      players=[PlayerConfig(player_id=f'{side}-{i}', name=f'{side.title()} Player {i}')
                               for i in range(1, 12)])


class ScenarioConfig(Model):
    engine_version: Literal['zone-engine/1'] = ENGINE_VERSION
    schema_version: Literal['sandbox/1'] = SCHEMA_VERSION
    seed: int = Field(default=7, ge=0, le=2_147_483_647)
    duration_seconds: int = Field(default=5400, ge=60, le=5400, multiple_of=2)
    preset: Literal['balanced', 'high-press', 'late-comeback', 'stalemate', 'custom'] = 'balanced'
    environment: Literal['neutral-dry'] = 'neutral-dry'
    home: TeamConfig = Field(default_factory=lambda: team('home'))
    away: TeamConfig = Field(default_factory=lambda: team('away'))

    @model_validator(mode='after')
    def unique_roster(self):
        ids = [p.player_id for t in (self.home, self.away) for p in t.players]
        if self.home.team_id == self.away.team_id or len(set(ids)) != 22:
            raise ValueError('teams and player IDs must be unique')
        return self


class Scenario(Model):
    scenario_id: str
    config_hash: Digest
    config: ScenarioConfig


class RngState(Model):
    key: Digest
    counter: int = Field(ge=0, le=100_000)


class ActorState(Model):
    player_id: Identifier
    team_id: Identifier
    role: Literal['GK', 'DF', 'MF', 'FW']
    stamina: int = Field(ge=0, le=10000)
    last_action_tick: int = Field(ge=0, le=5400)


class PendingAction(Model):
    tick: int = Field(ge=1, le=5400)
    order: int = Field(ge=1)
    kind: Literal['tactic', 'restart']
    team_id: Identifier
    field: Literal['formation', 'pressing', 'compactness', 'directness', 'tempo', 'risk'] | None = None
    value: int | str | None = None
    operation_id: Identifier | None = None


class EngineEvent(Model):
    sequence: int = Field(ge=1)
    tick: int = Field(ge=0, le=5400)
    period: Literal[1, 2]
    type: Literal['kickoff', 'pass', 'carry', 'pressure', 'tackle', 'interception', 'turnover',
                  'recovery', 'shot', 'goal', 'save', 'halftime', 'fulltime']
    team_id: Identifier | None = None
    actor_id: Identifier | None = None
    recipient_id: Identifier | None = None
    outcome: str | None = None
    x: int = Field(ge=0, le=100)
    y: int = Field(ge=0, le=100)
    end_x: int = Field(ge=0, le=100)
    end_y: int = Field(ge=0, le=100)
    possession_id: int = Field(ge=1)
    policy_revision: int = Field(ge=0)


class Intervention(Model):
    operation_id: Identifier
    expected_revision: int = Field(ge=0)
    requested_tick: int = Field(ge=0, le=5400)
    effective_tick: int = Field(ge=1, le=5400)
    team_id: Identifier
    field: str
    previous_value: int | str
    new_value: int | str
    result: Literal['accepted', 'applied']


class EngineState(Model):
    engine_version: Literal['zone-engine/1'] = ENGINE_VERSION
    schema_version: Literal['sandbox/1'] = SCHEMA_VERSION
    scenario: Scenario
    tick: int = Field(ge=0, le=5400)
    revision: int = Field(ge=0, le=2048)
    period: Literal[1, 2]
    lifecycle: Literal['paused', 'running', 'completed', 'cancelled']
    score: dict[str, int]
    possession_team_id: Identifier
    possession_actor_id: Identifier
    possession_id: int = Field(ge=1)
    ball_x: int = Field(ge=0, le=100)
    ball_y: int = Field(ge=0, le=100)
    actors: list[ActorState] = Field(min_length=22, max_length=22)
    tactics: dict[str, Tactics]
    policy_revision: int = Field(ge=0)
    rng: dict[str, RngState]
    pending: list[PendingAction] = Field(max_length=128)
    next_queue_order: int = Field(ge=1)
    next_decision_tick: int = Field(ge=1, le=5410)
    event_cursor: int = Field(ge=1, le=20000)
    events: list[EngineEvent] = Field(min_length=1, max_length=20000)
    interventions: list[Intervention] = Field(max_length=1024)


class Command(Model):
    operation_id: Identifier
    expected_revision: int = Field(ge=0, le=2048)
    kind: Literal['pause', 'resume', 'step', 'advance', 'intervene', 'cancel', 'checkpoint']
    ticks: int = Field(default=1, ge=1, le=300)
    team_id: Identifier | None = None
    field: Literal['formation', 'pressing', 'compactness', 'directness', 'tempo', 'risk'] | None = None
    value: int | str | None = None
    requested_tick: int | None = Field(default=None, ge=0, le=5400)

    @model_validator(mode='after')
    def shape(self):
        if self.kind == 'intervene':
            if self.team_id is None or self.field is None or self.value is None or self.requested_tick is None:
                raise ValueError('intervention requires team_id, field, value and requested_tick')
            Tactics.model_validate({self.field: self.value})
        elif any(x is not None for x in (self.team_id, self.field, self.value, self.requested_tick)):
            raise ValueError('tactical fields are only legal for interventions')
        if self.kind not in ('step', 'advance') and self.ticks != 1:
            raise ValueError('ticks only applies to step/advance')
        return self


class Snapshot(Model):
    engine_version: Literal['zone-engine/1'] = ENGINE_VERSION
    schema_version: Literal['sandbox/1'] = SCHEMA_VERSION
    state: EngineState
    state_hash: Digest


class RuntimeView(Model):
    session_id: str
    scenario_id: str
    tick: int
    revision: int
    event_cursor: int
    state_hash: Digest
    event_hash: Digest
    state: EngineState
    checkpoint_id: str | None = None


class MutationResult(Model):
    session_id: str
    scenario_id: str
    tick: int
    revision: int
    event_cursor: int
    lifecycle: str
    state_hash: Digest
    event_hash: Digest
    checkpoint_id: str | None = None


class AuditEntry(Model):
    session_id: str
    scenario_id: str
    command: Command
    result: Literal['accepted', 'rejected']
    code: str | None = None
    status_code: int = 200
    recorded_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tick: int
    revision: int
    event_cursor: int
    intervention: Intervention | None = None


class CreateSession(Model):
    operation_id: Identifier
    scenario_id: str = Field(pattern=r'^scenario-[0-9a-f]{64}$')


class RestoreRequest(Model):
    operation_id: Identifier
    expected_revision: int = Field(ge=0, le=2048)


class CheckpointView(Model):
    checkpoint_id: str
    session_id: str
    scenario_id: str
    tick: int
    revision: int
    event_cursor: int
    snapshot: Snapshot


class EventPage(Model):
    session_id: str
    tick: int
    revision: int
    event_cursor: int
    next_cursor: int
    events: list[EngineEvent]


class ReplayRecord(Model):
    command: Command
    state_hash: Digest
    event_hash: Digest


class Ancestor(Model):
    checkpoint_id: str
    session_id: str
    snapshot_hash: Digest
    revision: int = Field(ge=1, le=2048)


class ExperimentManifest(Model):
    engine_version: Literal['zone-engine/1'] = ENGINE_VERSION
    schema_version: Literal['sandbox/1'] = SCHEMA_VERSION
    rng_algorithm: Literal['sha256-counter/1'] = RNG_ALGORITHM
    implementation_hash: Digest
    rng_derivation: Literal['sha256(engine_version:seed:stream); sha256(key:counter)'] = 'sha256(engine_version:seed:stream); sha256(key:counter)'
    session_id: str
    scenario: Scenario
    ancestry: list[Ancestor] = Field(max_length=32)
    operations: list[ReplayRecord] = Field(max_length=2048)
    interventions: list[Intervention] = Field(max_length=1024)
    event_hashes: list[Digest] = Field(max_length=20000)
    state_hash: Digest
    event_hash: Digest
    execution: Literal['integer-seconds; max-command-ticks=300; manual-bounded-driver'] = 'integer-seconds; max-command-ticks=300; manual-bounded-driver'


class Verification(Model):
    verified: bool
    component: str | None = None
    operation_index: int | None = None
    expected: str | None = None
    actual: str | None = None


class ErrorDetail(Model):
    code: str


class ErrorResponse(Model):
    detail: ErrorDetail
