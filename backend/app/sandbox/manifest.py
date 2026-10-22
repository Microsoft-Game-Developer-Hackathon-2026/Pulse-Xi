"""Independent replay from resolved inputs, never from the claimed final state."""
from dataclasses import dataclass

from .engine import EngineError, apply_command, build_scenario, canonical, digest, initial_state, implementation_hash
from .models import EngineState, ExperimentManifest, Verification


@dataclass
class _VerifiedPrefix:
    """One bounded prefix, computed locally; never accepted from a wire payload.

    Only verify_bundle creates this per-request object. apply_command is
    copy-on-write, so suffix replay cannot mutate the verified parent state.
    """
    revision: int
    state: EngineState | None = None
    scenario: str = ''
    operations: tuple[str, ...] = ()
    ancestry: tuple[str, ...] = ()
    seen: frozenset[str] = frozenset()
    last_ancestor_revision: int = 0


def verify_manifest(manifest: ExperimentManifest, *, _prefix: _VerifiedPrefix | None = None) -> Verification:
    def mismatch(component, expected, actual, index=None):
        return Verification(verified=False, component=component, operation_index=index,
                            expected=str(expected), actual=str(actual))

    if manifest.implementation_hash != implementation_hash():
        return mismatch('implementation_hash', manifest.implementation_hash, implementation_hash())
    scenario = build_scenario(manifest.scenario.config)
    if scenario != manifest.scenario:
        return mismatch('scenario.config_hash', manifest.scenario.config_hash, scenario.config_hash)
    state = initial_state(scenario)
    seen = set()
    ancestry_index = 0
    last_ancestor_revision = 0
    start = 0
    if (_prefix is not None and _prefix.state is not None
            and canonical(scenario) == _prefix.scenario
            and tuple(canonical(r) for r in manifest.operations[:_prefix.revision]) == _prefix.operations
            and tuple(canonical(a) for a in manifest.ancestry[:len(_prefix.ancestry)]) == _prefix.ancestry):
        # Every skipped record and ancestor equals an already independently
        # verified input/hash record. Any difference takes the full replay path.
        state = _prefix.state
        seen = set(_prefix.seen)
        ancestry_index = len(_prefix.ancestry)
        last_ancestor_revision = _prefix.last_ancestor_revision
        start = _prefix.revision
    for index in range(start, len(manifest.operations)):
        record = manifest.operations[index]
        if record.command.operation_id in seen:
            return mismatch('operation_id', 'unique', record.command.operation_id, index)
        seen.add(record.command.operation_id)
        try:
            state = apply_command(state, record.command)
        except EngineError as error:
            return mismatch('command', 'legal operation', error.code, index)
        actual = digest(state)
        if actual != record.state_hash:
            return mismatch('operation.state_hash', record.state_hash, actual, index)
        if digest(state.events) != record.event_hash:
            return mismatch('operation.event_hash', record.event_hash, digest(state.events), index)
        while ancestry_index < len(manifest.ancestry) and manifest.ancestry[ancestry_index].revision == state.revision:
            ancestor = manifest.ancestry[ancestry_index]
            if (ancestor.snapshot_hash != actual or record.command.kind != 'checkpoint'
                    or ancestor.revision <= last_ancestor_revision):
                return mismatch('ancestry.snapshot_hash', ancestor.snapshot_hash, actual, index)
            # IDs are transport provenance; verify their deterministic checkpoint derivation.
            expected_id = 'checkpoint-' + digest([ancestor.session_id, record.command.operation_id])
            if ancestor.checkpoint_id != expected_id:
                return mismatch('ancestry.checkpoint_id', ancestor.checkpoint_id, expected_id, index)
            ancestry_index += 1
            last_ancestor_revision = ancestor.revision
        if _prefix is not None and _prefix.state is None and state.revision == _prefix.revision:
            _prefix.state = state
            _prefix.scenario = canonical(scenario)
            _prefix.operations = tuple(canonical(r) for r in manifest.operations[:index + 1])
            _prefix.ancestry = tuple(canonical(a) for a in manifest.ancestry[:ancestry_index])
            _prefix.seen = frozenset(seen)
            _prefix.last_ancestor_revision = last_ancestor_revision
    if ancestry_index != len(manifest.ancestry):
        return mismatch('ancestry.revision', 'visited checkpoint revisions', 'unresolved ancestry')
    if state.interventions != manifest.interventions:
        return mismatch('interventions', digest(manifest.interventions), digest(state.interventions))
    actual_hashes = [digest(e) for e in state.events]
    for i, (expected, actual) in enumerate(zip(manifest.event_hashes, actual_hashes)):
        if expected != actual:
            return mismatch(f'events[{i}].hash', expected, actual)
    if len(actual_hashes) != len(manifest.event_hashes):
        return mismatch('events.length', len(manifest.event_hashes), len(actual_hashes))
    if manifest.event_hash != digest(state.events):
        return mismatch('event_hash', manifest.event_hash, digest(state.events))
    if manifest.state_hash != digest(state):
        return mismatch('state_hash', manifest.state_hash, digest(state))
    return Verification(verified=True)
