# Broadcast studio contract proposal

> **Superseded:** the draft, approval and export workflow now exists. See [Director Studio draft contract](DIRECTOR_STUDIO.md) for the active API, producer authorization and audit behavior. Issue #17 remains open while its Foundry dependency (#14) awaits an explicitly approved live validation. The original proposal below is retained as design history and is not an accurate description of the current implementation.

## Existing behavior

`GET /api/matches/{match_id}/overlays` returns deterministically scheduled, non-overlapping `OverlayCue` values linked to verified insight packets. `GET /api/matches/{match_id}/overlays/{cue_id}` returns one cue for inspection/export. The current React command view previews the queue, controls its visibility, and exports JSON. These endpoints describe generated cues; they do not persist editorial changes or approvals.

The proposed studio keeps this read-only generated queue as the fallback. Source facts are immutable inputs; editorial choices are a separate draft; program output is a frozen approved revision.

## Version 1 editorial document

A studio document is scoped to one match and has a monotonically increasing revision:

```json
{
  "schema": "pulse-xi-broadcast-studio/1",
  "match_id": "fixture-identifier",
  "revision": 3,
  "updated_at": "2026-10-21T12:00:00Z",
  "updated_by": "producer-id",
  "cues": [
    {
      "cue_id": "existing-cue-id",
      "source_insight_id": "verified-insight-id",
      "evidence_event_ids": ["event-1", "event-2"],
      "source_revision": "verified-source-revision",
      "start_match_second": 612,
      "end_match_second": 624,
      "priority": 50,
      "template": "score_lower_third",
      "safe_area": "lower_third",
      "transition": "cut",
      "decision": "include"
    }
  ],
  "approval": null
}
```

The example is illustrative, not a real match record. `source_revision` must bind to the authoritative source revision/manifest supplied by the evidence contract; implementations must not invent a hash or revision. Match times are integer seconds in the existing replay clock, with a half-open interval `[start, end)`. For an existing generated cue, the initial range is copied from `start_match_second` and `end_match_second`; source truth, event IDs, metrics, and narrative are never editable.

Allowed initial templates are the visual templates already represented by verified cues: `score_lower_third` and `tactical_lower_third`. Allowed safe areas and transitions should be enumerated centrally in the implementation contract; v1 proposal uses `lower_third` and `cut` only. This intentionally avoids pretending that an unimplemented template or animation exists.

## Deterministic scheduling and validation

- Every cue must reference a currently visible, verified insight for the same match and the evidence event IDs must exactly match the verified packet.
- Reject unknown, stale, or unverified sources. A changed source revision invalidates the draft cue and any approval based on it.
- Require `0 <= start < end <= match.duration_seconds`; enforce a maximum duration of 60 seconds, matching the current `OverlayCue` bound.
- Reject overlapping included cue intervals. Adjacent intervals where one ends at second N and the next begins at N do not collide.
- `priority` is an integer 0–100. It orders the queue (higher first, then start time, then cue ID), but never silently resolves a collision. The editor must ask the operator to move, shorten, or exclude a cue.
- Excluded cues remain in the draft and audit history but do not appear in preview/program output.
- Validate template and safe-area values against server-side allowlists; ignore client-supplied output text, scores, metrics, or evidence.
- Revalidate the complete draft on every save and immediately before approval.

## Proposed API shape

These routes are proposals, not available endpoints:

| Method and route | Behavior |
| --- | --- |
| `GET /api/matches/{match_id}/studio` | Return current draft, revision, allowed choices, and available verified cues. |
| `PUT /api/matches/{match_id}/studio` | Save a complete draft with `If-Match: <revision>`; return 409 on stale revision and 422 on validation errors. |
| `POST /api/matches/{match_id}/studio/approve` | Approve the exact current revision with `If-Match`; return an immutable program export. |
| `GET /api/matches/{match_id}/studio/exports/{revision}` | Return the frozen export for that approved revision only. |

All write operations require an explicit producer authorization contract. The current shared import token is a data-import capability, not producer identity or approval authority, and must not be reused for studio edits. Until an appropriate identity/authorization design is reviewed, studio writes remain unimplemented. No anonymous or client-only approval is represented as authoritative.

Use typed errors: 401/403 for missing/insufficient producer authorization, 404 for unavailable match or source, 409 for stale revision or source, and 422 for invalid timing, collision, or allowlist value. Error responses must not include credentials or hidden/private scenario data.

## Approval and immutable export

Approval binds the editor identity, UTC timestamp, match ID, exact studio revision, and verified source revisions. An approved export is immutable. Any subsequent edit creates a new draft revision with no approval; it must be reapproved before it can be exported as program output.

`pulse-xi-broadcast-program/1` contains only included cues, sorted by start second, then descending priority, then cue ID. Each cue carries its ID, match interval, template, safe area, transition, source insight ID, evidence event IDs, and source revision. It does not duplicate mutable source narratives or claim that graphics were aired. Export metadata records schema, match ID, studio revision, approval record, and generation time. Generation time is metadata and does not affect cue ordering or content.

Preview and program modes consume the same deterministic draft/export representation. Preview displays “PREVIEW” and the selected match clock; program mode is available only for an approved immutable export and displays its approved revision. The countdown is `max(0, cue.start_match_second - replay_second)`; an expired cue is not queued as upcoming. Match clock changes never mutate or reapprove the document.

## Audit and operator workflow

Record append-only actions for cue include/exclude, timing changes, priority changes, template changes, save, approval, and export. Each action records operator, UTC time, match, base/result revision, cue ID when applicable, and a concise changed-field list. Do not log credentials, arbitrary prompts, or unrelated private scenario data. Failed optimistic writes do not create successful revision records.

Operator workflow:

1. Open the generated cue queue and select a verified cue with its evidence.
2. Set order/timing/template/safe area/transition or exclude it; see collision and stale-source errors inline.
3. Preview at the cue’s actual match time, with a visible preview label and countdown.
4. Save against the displayed revision. Resolve 409 by reloading and reviewing the latest draft, never by silently overwriting it.
5. Review the entire sequence and approve the exact revision.
6. Export only the frozen approved revision; retain the revision and approval metadata with the JSON.

The read-only overlay queue and JSON export remain available whenever studio persistence or producer authorization is unavailable.

## Accessibility and verification checklist

A future implementation should provide keyboard-operable reorder controls (with move up/down buttons in addition to drag), labeled time/template controls, focus-visible states, live announcements for save/conflict/approval outcomes, and a textual cue table equivalent to the 16:9 preview. Preview and program status must be distinguishable without color alone.

Required tests include interval boundary/collision and priority ordering, maximum duration, wrong-match and stale/unverified evidence, 409 optimistic conflict, source revision invalidation, immutable approved export, export schema/order, countdown at before/start/end times, approval authorization, keyboard reordering, and fallback to the existing read-only queue. These tests are acceptance criteria for implementation, not claims that this design-only change has executed them.

## Scope boundary

This proposal makes no live Foundry call, creates no broadcast artwork or trademark, and makes no deployment or provider-validation claim. It does not close issue #17. Implement the editor only after the prerequisite contracts are complete and reviewed; then link running backend and browser evidence to the implementation PR.
