# Checkpoint integration proposal (#6)

Status: **contract preparation only; restore is blocked by #3–#5**. No checkpoint endpoint, serializer, RNG snapshot or continuation result is implemented here. The metadata type is explicitly named ProposedCheckpointMetadata and is not connected to production controls. It wraps an opaque engine-state reference rather than introducing a second player, tactical, clock or RNG model.

## Required agreement with Diyan

The engine must own its complete snapshot schema, legal transaction boundary, canonicalization/hash algorithm and compatible engine/state versions. It must include all actual runtime fields: authoritative tick/period, score, ball/possession, actors/lineups, tactics, pending actions, all named RNG stream states/counters, delivery cursor and any other mutable continuation state. Diyan should identify every field by inspecting his implementation; this list is a review checklist, not a substitute state schema.

Checkpoint metadata proposes scenario/branch/checkpoint IDs, tick/revision/cursor, engine/state versions, state/event-stream hashes, creation UTC and an opaque engine_state_ref. The frontend metadata check catches incompatible identity/version/boundaries; it does **not** verify integrity, ownership, state completeness or resumability. Those are server and engine responsibilities.

## Proposed operation semantics (names/routes await #2)

- Save: authorized isolated session, expected revision and idempotency key. Under one SQLite transaction capture complete immutable engine state, pending queue/RNG streams and the exact committed event boundary/hash. Return metadata and current revision. Repeated same key/input returns the same checkpoint; conflicting reuse returns a conflict.
- Inspect: authorize scenario/branch ownership; expose safe metadata without raw secret/session data. Unknown or inaccessible checkpoint must not leak another user's state.
- Restore: expected revision, checkpoint ID and target isolation intent. Verify owner, compatible versions, full state integrity and event boundary. Create a new isolated runtime/branch; retain parent history. The engine reconstructs queue/RNG and returns its authoritative state/tick/revision/cursor. Never overwrite a completed match or independently advance a browser clock.
- Seek/step/pause/resume: use #4's real operations. Publish one authoritative tick and a monotonic revision; reject stale mutations. UI cancellation must not imply a committed server restore was rolled back: reconcile through a fresh authoritative snapshot.

No proposed route is registered until the engine adapter and authorization contract exist. The existing fixture replay is not a checkpoint implementation.

## UI state contract and failures

Metadata validation accepts unknown JSON at the boundary and returns diagnostic codes for malformed/null input rather than throwing. UTC timestamps require explicit seconds and a valid calendar date (optional millisecond precision); JavaScript's normalization of impossible dates is rejected. These checks remain metadata-only and cannot establish engine-state integrity or exact continuation.

The typed state union describes unavailable, loading, saving, restoring, ready and explicit errors. Unavailable means a readable dependency explanation with no fake save/restore controls. Mutations require single-flight progress, disabled duplicate actions, preserved current view on recoverable failure and confirmation before changing runtime context.

Required server codes: not_found (404), unauthorized (403 or concealed 404), stale_revision (409), incompatible_version (409), corrupt_snapshot (422), transaction_failed (503). Confirm these with the API owner. Missing RNG/queue data is corruption, never a default seed or empty queue. A concurrent restore may succeed only into distinct authorized runtimes; otherwise one must receive a revision conflict. Interrupted writes must remain atomic. Reconnect must reconcile an operation whose response was lost.

## Exact engine conformance tests required before #6 completion

Using Diyan's real engine fixture (not a fake event generator):

1. Run to a legal mid-match boundary, save, then finish with an explicit recorded future-input sequence.
2. Restore that checkpoint into a second runtime and apply the identical inputs. Compare canonical future event bytes/hash, final state hash, score, order, possession, pending queue and every RNG counter.
3. Repeat at kickoff, halftime, goal-adjacent boundaries and full time. Seek between boundaries and assert no later event or cue is visible.
4. Tamper one snapshot field, RNG stream, queue item, event hash or version and require rejection before mutation.
5. Test duplicate/conflicting idempotency keys, stale revisions, concurrent isolated restores, wrong scenario/branch/owner, interrupted transaction and a lost response followed by reconciliation.
6. Measure serialized bytes, save/restore time and worst-case seek latency with input size and hardware recorded.

The current tests validate **metadata only**. None of these engine-continuation tests is marked passed. #7 interventions can integrate after the engine-owned snapshot/restore hooks are agreed; #9 must supply canonical manifests instead of a parallel provenance format.
