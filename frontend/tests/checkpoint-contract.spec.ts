import { expect, test } from '@playwright/test'
import { checkpointMetadataProblems } from '../src/features/sandbox/checkpointContract'
import type { ProposedCheckpointMetadata } from '../src/features/sandbox/checkpointContract'

// Isolated development metadata. No checkpoint or engine execution is claimed.
const expected = { scenario_id: 'test-scenario', branch_id: 'test-branch', engine_version: 'test-engine', engine_state_schema_version: 'test-state' }
const metadata: ProposedCheckpointMetadata = {
  ...expected, schema_version: 'checkpoint-metadata/proposal-1', checkpoint_id: 'test-checkpoint',
  tick: 900, revision: 2, event_cursor: 50, state_hash: 'engine-owned-digest',
  event_stream_hash: 'engine-owned-event-digest', engine_state_ref: 'opaque-test-state',
  created_at_utc: '2026-10-16T00:00:00Z',
}

test('proposed checkpoint metadata retains scope and an opaque engine-state reference', () => {
  expect(checkpointMetadataProblems(metadata, expected)).toEqual([])
  expect('players' in metadata).toBe(false)
  expect('rng_state' in metadata).toBe(false)
})

test('checkpoint metadata rejects incompatible versions, scope and invalid boundaries', () => {
  expect(checkpointMetadataProblems({ ...metadata, branch_id: 'other' }, expected)).toContain('scope_mismatch')
  expect(checkpointMetadataProblems({ ...metadata, engine_version: 'other' }, expected)).toContain('incompatible_version')
  for (const tick of [-1, NaN, 1.5, Infinity]) expect(checkpointMetadataProblems({ ...metadata, tick }, expected)).toContain('invalid_boundary')
  expect(checkpointMetadataProblems({ ...metadata, state_hash: '' }, expected)).toContain('missing_provenance')
  expect(checkpointMetadataProblems({ ...metadata, created_at_utc: 'invalid' }, expected)).toContain('invalid_timestamp')
})
