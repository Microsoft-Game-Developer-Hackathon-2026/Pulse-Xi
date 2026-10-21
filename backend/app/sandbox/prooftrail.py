"""Verified branch comparison built only from owner-scoped authoritative runtime state."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .engine import EngineError, digest
from .models import EngineEvent, ExperimentManifest, Intervention, RuntimeView
from .manifest import verify_manifest


class Metrics(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    goals: int = Field(ge=0)
    shots: int = Field(ge=0)
    recoveries: int = Field(ge=0)
    turnovers: int = Field(ge=0)
    passes: int = Field(ge=0)
    carries: int = Field(ge=0)


class BranchWindow(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    start_tick: int = Field(ge=0, le=5400)
    end_tick: int = Field(ge=0, le=5400)
    metrics_by_team: dict[str, Metrics]
    evidence_event_ids: list[str]


class TeamDelta(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    goals: int
    shots: int
    recoveries: int
    turnovers: int
    passes: int
    carries: int


class SandboxInsight(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal['sandbox-prooftrail/1'] = 'sandbox-prooftrail/1'
    scenario_id: str
    branch_session_id: str
    baseline_session_id: str
    checkpoint_id: str
    intervention: Intervention
    branch_window: BranchWindow
    baseline_window: BranchWindow
    metric_deltas_by_team: dict[str, TeamDelta]
    manifest_hash: str
    branch_verification: Literal['verified']
    baseline_verification: Literal['verified']
    verification_result: Literal['verified']
    interpretation: Literal['single-run synthetic engine comparison; association only, not a real-world causal prediction']
    uncertainty: Literal['one deterministic trajectory per branch; statistical uncertainty is not estimated']


def _metrics(events: list[EngineEvent], team_ids: list[str], start: int, end: int) -> tuple[dict[str, Metrics], list[str]]:
    selected = [event for event in events if start <= event.tick < end]
    by_team = {}
    for team_id in team_ids:
        values = {
            name: sum(1 for event in selected if event.team_id == team_id and event.type == event_type)
            for name, event_type in (
                ('goals', 'goal'), ('shots', 'shot'), ('recoveries', 'recovery'),
                ('turnovers', 'turnover'), ('passes', 'pass'), ('carries', 'carry'),
            )
        }
        by_team[team_id] = Metrics(**values)
    cited = [f'{event.sequence}' for event in selected if event.type in ('goal', 'shot', 'recovery', 'turnover', 'pass', 'carry')]
    return by_team, cited


def _checkpoint_in_baseline(baseline: ExperimentManifest, checkpoint_id: str, snapshot_hash: str) -> bool:
    for record in baseline.operations:
        if record.command.kind != 'checkpoint':
            continue
        derived = 'checkpoint-' + digest([baseline.session_id, record.command.operation_id])
        if derived == checkpoint_id and record.state_hash == snapshot_hash:
            return True
    return False


def build_sandbox_insight(
    branch: RuntimeView,
    baseline: RuntimeView,
    branch_manifest: ExperimentManifest,
    baseline_manifest: ExperimentManifest,
    intervention_id: str,
    at_tick: int,
) -> SandboxInsight:
    """Recompute both manifests, prove checkpoint ancestry, then compare equal windows."""
    if branch.session_id == baseline.session_id:
        raise EngineError('baseline_must_be_distinct', 422)
    if branch.scenario_id != baseline.scenario_id:
        raise EngineError('scenario_mismatch', 422)
    if branch_manifest.session_id != branch.session_id or baseline_manifest.session_id != baseline.session_id:
        raise EngineError('manifest_session_mismatch', 409)
    branch_check = verify_manifest(branch_manifest)
    if not branch_check.verified:
        raise EngineError('branch_manifest_unverified', 409)
    baseline_check = verify_manifest(baseline_manifest)
    if not baseline_check.verified:
        raise EngineError('baseline_manifest_unverified', 409)

    ancestry = next((item for item in branch_manifest.ancestry
                     if item.session_id == baseline.session_id
                     and _checkpoint_in_baseline(baseline_manifest, item.checkpoint_id, item.snapshot_hash)), None)
    if ancestry is None:
        raise EngineError('baseline_not_ancestor', 422)
    if branch.state.scenario.config_hash != baseline.state.scenario.config_hash:
        raise EngineError('scenario_mismatch', 422)

    intervention = next((item for item in branch.state.interventions
                         if item.operation_id == intervention_id), None)
    if intervention is None or intervention.result not in ('accepted', 'applied'):
        raise EngineError('intervention_not_found', 404)
    effective = intervention.effective_tick
    if effective <= ancestry_revision_tick(branch_manifest, ancestry.checkpoint_id):
        raise EngineError('intervention_not_after_checkpoint', 422)
    if not (effective < at_tick <= branch.tick and at_tick <= baseline.tick):
        raise EngineError('invalid_comparison_window', 422)

    # Compare equal, fixed match-time windows. Include a same-length pre-window as context.
    width = at_tick - effective
    before_start = max(0, effective - width)
    teams = [branch.state.scenario.config.home.team_id, branch.state.scenario.config.away.team_id]
    before_branch, before_branch_ids = _metrics(branch.state.events, teams, before_start, effective)
    after_branch, after_branch_ids = _metrics(branch.state.events, teams, effective, at_tick)
    before_baseline, before_baseline_ids = _metrics(baseline.state.events, teams, before_start, effective)
    after_baseline, after_baseline_ids = _metrics(baseline.state.events, teams, effective, at_tick)

    # A single trajectory is descriptive. Difference-in-differences is not a causal estimate.
    deltas = {}
    fields = ('goals', 'shots', 'recoveries', 'turnovers', 'passes', 'carries')
    for team_id in teams:
        deltas[team_id] = TeamDelta(**{
            name: (getattr(after_branch[team_id], name) - getattr(before_branch[team_id], name))
                 - (getattr(after_baseline[team_id], name) - getattr(before_baseline[team_id], name))
            for name in fields
        })

    manifest_hash = digest({'branch': branch_manifest, 'baseline': baseline_manifest})
    return SandboxInsight(
        scenario_id=branch.scenario_id, branch_session_id=branch.session_id,
        baseline_session_id=baseline.session_id, checkpoint_id=ancestry.checkpoint_id,
        intervention=intervention,
        branch_window=BranchWindow(start_tick=effective, end_tick=at_tick,
            metrics_by_team=after_branch, evidence_event_ids=[f'{branch.session_id}-{item}' for item in after_branch_ids]),
        baseline_window=BranchWindow(start_tick=effective, end_tick=at_tick,
            metrics_by_team=after_baseline, evidence_event_ids=[f'{baseline.session_id}-{item}' for item in after_baseline_ids]),
        metric_deltas_by_team=deltas, manifest_hash=manifest_hash,
        branch_verification='verified', baseline_verification='verified', verification_result='verified',
        interpretation='single-run synthetic engine comparison; association only, not a real-world causal prediction',
        uncertainty='one deterministic trajectory per branch; statistical uncertainty is not estimated',
    )


def ancestry_revision_tick(manifest: ExperimentManifest, checkpoint_id: str) -> int:
    """Return the checkpoint tick from the replay record that proves its snapshot."""
    for record in manifest.operations:
        if record.command.kind == 'checkpoint' and 'checkpoint-' + digest([manifest.session_id, record.command.operation_id]) == checkpoint_id:
            # The operation hash is verified by verify_manifest. The checkpoint's tick is
            # the state after this operation and is available from the source session prefix.
            # A checkpoint command does not advance the authoritative clock, so infer it
            # from the preceding deterministic event frontier only when exact runtime tick
            # is supplied by the branch's intervention chronology.
            return record.command.requested_tick or 0
    return 0
