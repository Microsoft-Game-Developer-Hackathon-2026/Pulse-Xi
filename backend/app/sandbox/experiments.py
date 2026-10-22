"""Compute comparisons from actual branch events and independently verify bundles."""
from pydantic import Field
from pathlib import Path
from typing import Literal

from . import storage
from .control import Experiment, ExperimentRequest, read, trial_commands
from .engine import EngineError, apply_command, digest, restore_state, implementation_hash
from .manifest import verify_manifest
from .models import ExperimentManifest, Model, Snapshot, Verification, Digest

METRICS = ('possessions', 'pressures', 'recoveries', 'turnovers', 'final_third_entries', 'shots', 'goals', 'activity', 'involvements')


class Evidence(Model):
    trial: int
    arm: Literal['baseline', 'variation']
    session_id: str = Field(pattern=r'^runtime-[0-9a-f]{64}$')
    sequence: int
    tick: int
    type: str
    actor_id: str | None
    contribution: int


class Summary(Model):
    mean: float
    minimum: int
    maximum: int
    samples: int


class Metric(Model):
    team_id: str
    metric: str
    baseline: Summary
    variation: Summary
    difference: float
    evidence_count: int
    evidence: list[Evidence] = Field(max_length=40)
    evidence_truncated: bool


class Trial(Model):
    trial: int
    initial_seed: int
    rng_counter_offset: int
    baseline_session_id: str
    variation_session_id: str
    baseline_event_hash: str
    variation_event_hash: str
    baseline_state_hash: str
    variation_state_hash: str


class Comparison(Model):
    schema_version: Literal['forkcast/1'] = 'forkcast/1'
    experiment_id: str
    checkpoint_id: str
    parent_state_hash: str
    start_tick: int
    end_tick: int
    trials: list[Trial]
    metrics: list[Metric]
    player_involvement: dict[str, dict[str, float]]
    verification_status: str = 'verified_rule_based'
    limitation: str = 'Descriptive synthetic-model trials, not calibrated probabilities or real-match predictions. Possession is event-derived, not tracking time.'


class ExperimentBundle(Model):
    schema_version: Literal['forkcast-manifest/1'] = 'forkcast-manifest/1'
    implementation_hash: Digest
    experiment: Experiment
    parent: Snapshot
    branches: list[ExperimentManifest] = Field(min_length=2, max_length=10)
    comparison_hash: Digest


def experiment_implementation_hash():
    return digest({'core': implementation_hash(), **{name: (Path(__file__).parent / name).read_text(encoding='utf-8')
                   for name in ('control.py', 'experiments.py')}})


def summarize(values):
    return Summary(mean=round(sum(values) / len(values), 6), minimum=min(values), maximum=max(values), samples=len(values))


def calculate(experiment: Experiment, parent, states, manifests) -> Comparison:
    teams = (parent.scenario.config.home.team_id, parent.scenario.config.away.team_id)
    vectors, references = [], {}
    involvement = {'baseline': {}, 'variation': {}}
    for index, state in enumerate(states):
        arm, trial = ('baseline' if index % 2 == 0 else 'variation'), index // 2
        counts = {(t, metric): 0 for t in teams for metric in METRICS}
        possessions = {t: set() for t in teams}
        for event in state.events[parent.event_cursor:]:
            t = event.team_id
            if t not in teams:
                continue
            contributions = {}
            if event.type == 'pressure': contributions['pressures'] = 1
            if event.type == 'recovery': contributions['recoveries'] = 1
            if event.type == 'turnover': contributions['turnovers'] = 1
            if event.type == 'shot': contributions['shots'] = 1
            if event.type == 'goal': contributions['goals'] = 1
            if event.type in ('kickoff', 'pass', 'carry', 'shot', 'goal', 'recovery', 'interception', 'tackle') and event.possession_id not in possessions[t]:
                possessions[t].add(event.possession_id)
                contributions['possessions'] = 1
            x, end_x = (event.x, event.end_x) if t == teams[0] else (100 - event.x, 100 - event.end_x)
            if event.type in ('pass', 'carry') and event.outcome == 'complete' and x < 66 <= end_x:
                contributions['final_third_entries'] = 1
            if event.actor_id:
                contributions['involvements'] = 1
                involvement[arm][event.actor_id] = involvement[arm].get(event.actor_id, 0) + 1
            weight = {'pass': 1, 'carry': 1, 'pressure': 1, 'recovery': 2, 'shot': 3}.get(event.type, 0)
            if weight: contributions['activity'] = weight
            for metric, value in contributions.items():
                counts[t, metric] += value
                references.setdefault((t, metric), []).append(Evidence(trial=trial, arm=arm,
                    session_id=manifests[index].session_id, sequence=event.sequence, tick=event.tick,
                    type=event.type, actor_id=event.actor_id, contribution=value))
        vectors.append(counts)
    metrics = []
    for t in teams:
        for metric in METRICS:
            a = summarize([vectors[i][t, metric] for i in range(0, len(vectors), 2)])
            b = summarize([vectors[i][t, metric] for i in range(1, len(vectors), 2)])
            refs = references.get((t, metric), [])
            metrics.append(Metric(team_id=t, metric=metric, baseline=a, variation=b,
                difference=round(b.mean - a.mean, 6), evidence_count=len(refs), evidence=refs[:40], evidence_truncated=len(refs) > 40))
    trials = [Trial(trial=i, initial_seed=parent.scenario.config.seed, rng_counter_offset=i * 4096,
        baseline_session_id=manifests[2*i].session_id, variation_session_id=manifests[2*i+1].session_id,
        baseline_event_hash=digest(states[2*i].events), variation_event_hash=digest(states[2*i+1].events),
        baseline_state_hash=digest(states[2*i]), variation_state_hash=digest(states[2*i+1])) for i in range(experiment.request.trials)]
    return Comparison(experiment_id=experiment.experiment_id, checkpoint_id=experiment.request.checkpoint_id,
        parent_state_hash=digest(parent), start_tick=parent.tick, end_tick=parent.tick + experiment.request.horizon,
        trials=trials, metrics=metrics,
        player_involvement={arm: {pid: round(count / experiment.request.trials, 6) for pid, count in sorted(players.items())}
                            for arm, players in involvement.items()})


def verify_bundle(bundle: ExperimentBundle) -> Verification:
    experiment = bundle.experiment
    if bundle.implementation_hash != experiment_implementation_hash():
        return Verification(verified=False, component='implementation_hash')
    try:
        parent = restore_state(bundle.parent)
    except EngineError as error:
        return Verification(verified=False, component='parent.' + error.code)
    if (experiment.status != 'completed' or experiment.branch_index != 2 * experiment.request.trials or experiment.command_index != 0
            or parent.lifecycle != 'paused' or parent.tick + experiment.request.horizon > parent.scenario.config.duration_seconds
            or len(bundle.branches) != 2 * experiment.request.trials
            or len(experiment.branches) != len(bundle.branches)
            or experiment.parent_state_hash != digest(parent)
            or experiment.start_tick != parent.tick or experiment.request.expected_revision != parent.revision):
        return Verification(verified=False, component='experiment.boundary')
    states = []
    for index, manifest in enumerate(bundle.branches):
        result = verify_manifest(manifest)
        if not result.verified:
            result.component = f'branches[{index}].{result.component}'
            return result
        if (manifest.session_id != experiment.branches[index] or not manifest.ancestry
                or manifest.ancestry[-1].checkpoint_id != experiment.request.checkpoint_id
                or manifest.ancestry[-1].session_id != experiment.parent_session_id
                or manifest.ancestry[-1].revision != parent.revision
                or manifest.ancestry[-1].snapshot_hash != digest(parent)):
            return Verification(verified=False, component=f'branches[{index}].ancestry')
        expected = trial_commands(experiment, index)
        if [r.command for r in manifest.operations[parent.revision:]] != expected:
            return Verification(verified=False, component=f'branches[{index}].inputs')
        # verify_manifest already replayed every prefix operation from kickoff
        # and checked this ancestor's hash at its exact revision. Reconstruct
        # only the trial suffix from that same verified immutable parent.
        state = parent
        for record in manifest.operations[parent.revision:]:
            state = apply_command(state, record.command)
        states.append(state)
    if (experiment.session_id != bundle.branches[-1].session_id or experiment.tick != states[-1].tick
            or experiment.revision != states[-1].revision or experiment.event_cursor != states[-1].event_cursor):
        return Verification(verified=False, component='experiment.progress')
    comparison = calculate(experiment, parent, states, bundle.branches)
    if digest(comparison) != bundle.comparison_hash:
        return Verification(verified=False, component='comparison_hash', expected=bundle.comparison_hash, actual=digest(comparison))
    return Verification(verified=True)


def _verified_comparison(owner, identity) -> tuple[ExperimentBundle, Comparison]:
    experiment = read('experiments', owner, identity)[1]
    if experiment.status != 'completed':
        raise EngineError('experiment_not_completed')
    checkpoint = storage.get_checkpoint(owner, experiment.request.checkpoint_id)
    manifests = [storage.manifest_at(owner, sid, experiment.request.expected_revision + len(trial_commands(experiment, index)))
                 for index, sid in enumerate(experiment.branches)]
    states = []
    for manifest in manifests:
        # This provisional calculation is never returned before verify_bundle
        # independently validates the full history and its checkpoint ancestry.
        state = checkpoint.snapshot.state
        for record in manifest.operations[experiment.request.expected_revision:]:
            state = apply_command(state, record.command)
        states.append(state)
    comparison = calculate(experiment, checkpoint.snapshot.state, states, manifests)
    result = ExperimentBundle(implementation_hash=experiment_implementation_hash(), experiment=experiment, parent=checkpoint.snapshot,
                              branches=manifests, comparison_hash=digest(comparison))
    verified = verify_bundle(result)
    if not verified.verified:
        raise EngineError('experiment_diverged', 422)
    # verify_bundle independently replays these captured manifests and checks
    # comparison_hash. Reuse the matching calculation from this same request;
    # replaying yet again cannot improve its verified source boundary.
    return result, comparison


def bundle(owner, identity) -> ExperimentBundle:
    return _verified_comparison(owner, identity)[0]


def comparison(owner, identity) -> Comparison:
    return _verified_comparison(owner, identity)[1]
