/** Proposed display DTO, not an implemented experiment API or manifest format. */
export type ComparisonMetricId = 'possession_sequences' | 'completed_passes' | 'recoveries' | 'turnovers' | 'pressure_events' | 'final_third_entries' | 'shots' | 'goals' | 'momentum_points'
export type DescriptiveSummary = { mean: number | null; min: number | null; max: number | null }
export type ComparisonEvidence = { event_id: string; branch_id: string; trial_id: string; match_second: number }
export type ComparisonMetric = {
  metric_id: ComparisonMetricId; units: 'event count' | 'sequence count' | 'activity points'
  baseline: DescriptiveSummary; alternative: DescriptiveSummary; mean_delta: number | null
  supporting_events: ComparisonEvidence[]; unavailable_reason: string | null
}
export type ProposedExperimentComparison = {
  schema_version: 'comparison/proposal-1'
  source: 'development_fixture' | 'authoritative_engine'
  experiment_id: string; scenario_id: string; match_id: string
  engine_version: string; manifest_ref: string
  parent_checkpoint: { checkpoint_id: string; state_hash: string; match_second: number }
  window: { start_second: number; end_second: number }; at_second: number
  baseline: { branch_id: string; label: string; intervention_summary: string; trial_hashes: Record<string, string> }
  alternative: { branch_id: string; label: string; intervention_summary: string; trial_hashes: Record<string, string> }
  paired_trial_ids: string[]; paired_seeds: number[]
  metrics: ComparisonMetric[]; limitations: string[]
  verification_status: 'unverified' | 'verified_rule_based'
}

const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown): value is string => typeof value === 'string' && !!value.trim() && value.length <= 4096
const numeric = (value: unknown) => typeof value === 'number'
const nullableNumber = (value: unknown) => value === null || numeric(value)
function comparisonShape(value: unknown): value is ProposedExperimentComparison {
  if (!record(value) || !record(value.parent_checkpoint) || !record(value.window)) return false
  if (!['schema_version', 'source', 'experiment_id', 'scenario_id', 'match_id', 'engine_version', 'manifest_ref', 'verification_status'].every(key => text(value[key]))) return false
  if (!text(value.parent_checkpoint.checkpoint_id) || !text(value.parent_checkpoint.state_hash) || !numeric(value.parent_checkpoint.match_second) ||
      !numeric(value.window.start_second) || !numeric(value.window.end_second) || !numeric(value.at_second)) return false
  for (const branch of [value.baseline, value.alternative]) {
    if (!record(branch) || !['branch_id', 'label', 'intervention_summary'].every(key => text(branch[key])) ||
        !record(branch.trial_hashes) || !Object.values(branch.trial_hashes).every(text)) return false
  }
  if (!Array.isArray(value.paired_trial_ids) || !value.paired_trial_ids.every(text) ||
      !Array.isArray(value.paired_seeds) || !value.paired_seeds.every(numeric) ||
      !Array.isArray(value.limitations) || !value.limitations.every(text) ||
      !Array.isArray(value.metrics) || value.metrics.length > 9) return false
  for (const metric of value.metrics) {
    if (!record(metric) || !text(metric.metric_id) || !text(metric.units) || !nullableNumber(metric.mean_delta) ||
        !(metric.unavailable_reason === null || text(metric.unavailable_reason)) ||
        !Array.isArray(metric.supporting_events) || metric.supporting_events.length > 10_000) return false
    if (![metric.baseline, metric.alternative].every(summary => record(summary) &&
      ['mean', 'min', 'max'].every(key => nullableNumber(summary[key])))) return false
    if (!metric.supporting_events.every(event => record(event) && ['event_id', 'branch_id', 'trial_id'].every(key => text(event[key])) && numeric(event.match_second))) return false
  }
  return true
}

export function comparisonProblems(value: unknown): string[] {
  const errors: string[] = []
  if (!comparisonShape(value)) return ['Malformed or incomplete comparison data.']
  if (!['unverified', 'verified_rule_based'].includes(value.verification_status) ||
      value.source === 'development_fixture' && value.verification_status !== 'unverified') errors.push('Invalid comparison verification status.')
  if (!['development_fixture', 'authoritative_engine'].includes(value.source)) errors.push('Unknown comparison source.')
  if (value.schema_version !== 'comparison/proposal-1') errors.push('Unsupported comparison schema.')
  if (!value.experiment_id || !value.scenario_id || !value.match_id || !value.engine_version || !value.manifest_ref || !value.parent_checkpoint.state_hash) errors.push('Comparison provenance is incomplete.')
  if (!value.baseline.branch_id || !value.alternative.branch_id || value.baseline.branch_id === value.alternative.branch_id) errors.push('Distinct branch identities are required.')
  const times = [value.parent_checkpoint.match_second, value.window.start_second, value.window.end_second, value.at_second]
  if (!times.every(time => Number.isSafeInteger(time) && time >= 0) ||
      times.some((time, index) => index > 0 && time < times[index - 1])) errors.push('Comparison window or replay cutoff is invalid.')
  if (!value.paired_trial_ids.length || value.paired_trial_ids.length > 20 ||
      new Set(value.paired_trial_ids).size !== value.paired_trial_ids.length ||
      value.paired_trial_ids.length !== value.paired_seeds.length ||
      !value.paired_seeds.every(seed => Number.isSafeInteger(seed) && seed >= 0)) errors.push('Paired trials/seeds are invalid or exceed the proposed limit.')
  for (const branch of [value.baseline, value.alternative]) {
    if (Object.keys(branch.trial_hashes).length !== value.paired_trial_ids.length ||
        value.paired_trial_ids.some(id => !Object.hasOwn(branch.trial_hashes, id))) errors.push('Paired trial output hashes do not match the trial set.')
  }
  if (new Set(value.metrics.map(metric => metric.metric_id)).size !== value.metrics.length) errors.push('Duplicate metric definitions.')
  for (const metric of value.metrics) {
    if (!['possession_sequences', 'completed_passes', 'recoveries', 'turnovers', 'pressure_events', 'final_third_entries', 'shots', 'goals', 'momentum_points'].includes(metric.metric_id)) errors.push('Unknown comparison metric.')
    const expectedUnits = metric.metric_id === 'possession_sequences' ? 'sequence count' : metric.metric_id === 'momentum_points' ? 'activity points' : 'event count'
    if (metric.units !== expectedUnits) errors.push(`Metric units disagree: ${metric.metric_id}.`)
    for (const summary of [metric.baseline, metric.alternative]) {
      const values = [summary.mean, summary.min, summary.max]
      const absent = values.every(item => item === null)
      if (!absent && (!values.every(item => item !== null && Number.isFinite(item) && item >= 0) ||
          summary.min! > summary.mean! || summary.mean! > summary.max!)) errors.push(`Invalid descriptive values: ${metric.metric_id}.`)
      if (!absent && value.paired_trial_ids.length === 1 && (summary.min !== summary.mean || summary.max !== summary.mean)) errors.push(`Single-trial range disagrees: ${metric.metric_id}.`)
    }
    if (metric.baseline.mean === null || metric.alternative.mean === null) {
      if (metric.mean_delta !== null || !metric.unavailable_reason) errors.push(`Missing unavailable reason: ${metric.metric_id}.`)
    } else if (metric.mean_delta === null || !Number.isFinite(metric.mean_delta) ||
      Math.abs(metric.mean_delta - (metric.alternative.mean - metric.baseline.mean)) > 1e-9) errors.push(`Calculated difference disagrees: ${metric.metric_id}.`)
    if (metric.supporting_events.some(event => !event.event_id ||
      ![value.baseline.branch_id, value.alternative.branch_id].includes(event.branch_id) ||
      !value.paired_trial_ids.includes(event.trial_id) || !Number.isSafeInteger(event.match_second) ||
      event.match_second <= value.window.start_second || event.match_second > value.window.end_second)) errors.push(`Unsupported event scope/time: ${metric.metric_id}.`)
    if (new Set(metric.supporting_events.map(event => JSON.stringify([event.branch_id, event.trial_id, event.event_id]))).size !== metric.supporting_events.length) errors.push(`Duplicate evidence: ${metric.metric_id}.`)
  }
  return errors
}
