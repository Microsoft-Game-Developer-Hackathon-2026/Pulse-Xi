# Director Studio draft contract

The existing `GET /api/matches/{match_id}/overlays` and cue JSON routes remain read-only deterministic schedules. The local Director Studio uses a separate `director-studio/1` draft contract:

- `GET /api/matches/{match_id}/studio` loads the current draft, source-backed cues, revision, approval status and recent audit actions.
- `PUT /api/matches/{match_id}/studio` saves bounded editorial fields with an `expected_revision`. It rejects stale revisions, unknown cue IDs, duplicate order values, mismatched templates, invalid times, post-match durations and overlapping cues.
- `POST /api/matches/{match_id}/studio/approve` approves exactly the current revision. The server re-resolves verified overlay sources and stores an immutable `director-studio-export/1` snapshot.
- `GET /api/matches/{match_id}/studio/export[?revision=N]` returns the latest approved immutable snapshot or a specific approved revision.

Every route requires the import bearer token and `PULSE_ENABLE_LOCAL_DATA_ADMIN=1` on a direct loopback connection. The public-readonly boundary denies these routes. Secrets are held in the editor's component state and are not persisted. Editorial settings cannot replace source text, metrics, insight IDs, or evidence IDs. Audit records store action, revision and UTC time; they do not store credentials.
