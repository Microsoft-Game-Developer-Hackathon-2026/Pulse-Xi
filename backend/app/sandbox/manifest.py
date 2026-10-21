"""Independent replay from resolved inputs, never from the claimed final state."""
from .engine import EngineError, apply_command, build_scenario, digest, initial_state, implementation_hash
from .models import ExperimentManifest, Verification


def verify_manifest(manifest: ExperimentManifest) -> Verification:
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
    for index, record in enumerate(manifest.operations):
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
