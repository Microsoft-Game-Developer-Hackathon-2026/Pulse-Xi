/** Proposal only: metadata around Diyan's opaque authoritative state.
 * This neither serializes engine state nor authorizes or performs a restore.
 */
export type ProposedCheckpointMetadata = {
  schema_version: 'checkpoint-metadata/proposal-1'
  checkpoint_id: string; scenario_id: string; branch_id: string
  tick: number; revision: number; event_cursor: number
  engine_version: string; engine_state_schema_version: string
  state_hash: string; event_stream_hash: string; created_at_utc: string
  engine_state_ref: string
}

export type CheckpointUiState =
  | { status: 'unavailable'; reason: string }
  | { status: 'loading' | 'saving' | 'restoring' }
  | { status: 'ready'; checkpoints: ProposedCheckpointMetadata[] }
  | { status: 'error'; code: 'not_found' | 'unauthorized' | 'stale_revision' | 'incompatible_version' | 'corrupt_snapshot' | 'transaction_failed'; message: string; retryable: boolean }

export function checkpointMetadataProblems(value: ProposedCheckpointMetadata, expected: {
  scenario_id: string; branch_id: string; engine_version: string; engine_state_schema_version: string
}): string[] {
  const problems: string[] = []
  if (value.schema_version !== 'checkpoint-metadata/proposal-1') problems.push('metadata_schema_mismatch')
  if (value.scenario_id !== expected.scenario_id || value.branch_id !== expected.branch_id) problems.push('scope_mismatch')
  if (value.engine_version !== expected.engine_version || value.engine_state_schema_version !== expected.engine_state_schema_version) problems.push('incompatible_version')
  if (![value.tick, value.revision, value.event_cursor].every(item => Number.isSafeInteger(item) && item >= 0)) problems.push('invalid_boundary')
  if (![value.checkpoint_id, value.scenario_id, value.branch_id, value.engine_state_ref, value.state_hash, value.event_stream_hash].every(item => typeof item === 'string' && item.trim().length > 0)) problems.push('missing_provenance')
  if (!/^\d{4}-\d\d-\d\dT.*Z$/.test(value.created_at_utc) || !Number.isFinite(Date.parse(value.created_at_utc))) problems.push('invalid_timestamp')
  return problems
}
