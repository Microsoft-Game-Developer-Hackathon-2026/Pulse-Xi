import type { ProposedExperimentComparison } from '../src/features/experiments/comparisonContract'

// Development-only values; no engine or experiment has run.
export const fixture: ProposedExperimentComparison = {
  schema_version: 'comparison/proposal-1', source: 'development_fixture',
  experiment_id: 'fixture-experiment', scenario_id: 'fixture-scenario', match_id: 'fixture-match',
  engine_version: 'NO_ENGINE_EXECUTED', manifest_ref: 'DEVELOPMENT_FIXTURE_NOT_A_REAL_MANIFEST',
  parent_checkpoint: { checkpoint_id: 'fixture-checkpoint', state_hash: 'fixture-parent-hash', match_second: 3600 },
  window: { start_second: 3600, end_second: 5400 }, at_second: 5400,
  baseline: { branch_id: 'fixture-A', label: 'Original setup', intervention_summary: 'Development baseline values', trial_hashes: { t1: 'fixture-hash-A' } },
  alternative: { branch_id: 'fixture-B', label: 'Alternative setup', intervention_summary: 'Development comparison values', trial_hashes: { t1: 'fixture-hash-B' } },
  paired_trial_ids: ['t1'], paired_seeds: [123], verification_status: 'unverified',
  metrics: [{ metric_id: 'shots', units: 'event count', baseline: { mean: 2, min: 2, max: 2 }, alternative: { mean: 3, min: 3, max: 3 }, mean_delta: 1, unavailable_reason: null,
    supporting_events: [{ event_id: 'fixture-event', branch_id: 'fixture-B', trial_id: 't1', match_second: 4000 }] }],
  limitations: ['Isolated UI fixture. No checkpoint, tactical intervention or branch execution occurred.', 'Real paired-trial manifests and verifier output are required before product integration.'],
}
