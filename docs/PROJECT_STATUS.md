# Current project status - 2026-10-21


## Current Satvik acceptance boundary (2026-10-21)

Verified main is `4d8a01e`; live runtime consumers are forward-integration #53,
not established as main by older PRs merged into intermediate branches.

| Assigned issue | Implemented boundary | Remaining acceptance gate |
|---|---|---|
| #6 Checkpoints | Canonical save/isolated restore/parity in engine; #59 adds original snapshot and server-replayed historical state inspection, terminal checkpoints and measurements | Diyan runtime/consumer review and integration |
| #8 ForkCast | Real paired trials, comparisons and provenance; #59 adds explicit independent verification and cited source-branch navigation | Diyan/Mahir review and integration |
| #10 Control Room | Actual operator APIs, refresh/retry and analysis; #59 fixes retained private retry state after disconnect | #53/#59 review and integration |
| #11 Observer | Recorded snapshots, lazy scene/cameras/profiles/fallback; physical Iris Xe probe recorded in #59 | Runtime consumer review; continuous actor frames unavailable, never inferred |
| #12 Blender | Seven GLBs pass unchanged manifest/hash/geometry contract; Blender 5.2.2 temporary export/reimport passes | #31 rights-holder provenance/licensing/release approval remains required |
| #27 Pass Difficulty | Existing versioned formula, verifier, factors/player summaries/exports; runtime #53 and native #57 adapters tested | Native/runtime integration reviews |

#57 and #58 are implemented and exact-head CI verified, with required reviews
pending. #54 is the separately reviewed ProofTrail request-isolation correction
for #51. Validation branches may combine #42/#48/#51/#54 for testing; they are
not substitutes for review or main integration. #32/#33 remain historical
preparation work; implemented engine contracts supersede those proposals and
must not be overwritten by them. No issue is closed by this status update.

The measurements and reproduction commands in [LIVE_SANDBOX](LIVE_SANDBOX.md)
include bounded local checkpoint/ForkCast and physical Intel Iris Xe evidence.
Earlier reports below describe their recorded revisions and remain historical.

## Current integration boundary

Observed main is `4d8a01e5e3483f6a4aafb62cd09def6fcfdd3713`: engine foundation #40 and trace authorization #45 are included. PRs #41, #46, #43 and #47 were merged into intermediate feature branches; their merged status alone does not establish main availability.

`integration/runtime-platform-main` forwards the published live Sandbox, architecture and runtime analysis implementations through normal merges, retaining Foundry command hardening from the separate main-targeted PR #52. It preserves the Vite 7.3.7 correction. No asset/preparation or independent teammate feature branch is absorbed. Review and exact-head CI remain required; this validation branch is not a claim that main has these features.

The forward-integration backend run passed **185 tests**. Both file-only verifiers returned `verified: true`; strict TypeScript/build and the baseline **42 browser cases** passed. A new real-browser regression reproduced unsaved analyst notes being erased by checkpoint revision refreshes. The analysis controls now stay mounted while stale content is hidden, preserving drafts and observer preferences without showing an obsolete boundary. Final browser/CI results belong to the forward-integration PR.

## Historical branch verification

The sections below preserve earlier branch evidence and review context. Their open/merged descriptions and counts are historical; use the current boundary above and live GitHub PR state for integration decisions.

## Authoritative engine branch

The engine foundation PR #40 adds scenario configuration, deterministic bounded transitions, durable sessions, revision/idempotency controls, complete checkpoint capture/restore, isolated branches, effective-tick tactics and replayable manifests. Its follow-up implements the live Control Room, durable server runs, authenticated snapshot/delta observer, historical seek and verified paired ForkCast with source-event drilldown and file-only experiment verification. See [the actual workflow and contracts](LIVE_SANDBOX.md). Foundation verification was 148 backend tests and 33 browser cases; the follow-up adds integration/recovery/concurrency/backup and browser workflow tests. These are branch results, not evidence of a merge or teammate approval. Shared contract review remains open. The asset and preparation PRs are untouched.

Follow-up local verification: **171 backend tests and 39 browser cases passed**, including all previous regressions; strict TypeScript/production build and both independent file-only verifiers passed. The run/experiment tests use actual transitions and SQLite, including multi-worker retries, process recovery, cancellation, historical boundaries and paired comparison verification. GitHub CI results are recorded on the follow-up PR.

## Integrated product

- Seeded synthetic fixtures, REST/WebSocket replay, event-derived analytics and SQLite persistence.
- Pass Difficulty (#28), replay Sandbox subset (#29), optional procedural 3D event observer (#30), persistent browser-local analysis, bookmarks and verified exports (#37).
- Match Data Hub (#38, merged at `9eeeb2d74feb61fa4783ebfeb994f2a2f8044126`): canonical JSON validation/preview, authorized atomic import, searchable library, quality inspection and portable packages.

## Issue #2 architecture audit (historical inspection)

Live browser inspection confirms main 50f72e2, open #40 (224be7c) -> main,
open #41 (f2854ae) -> engine branch, open #43 (b715e6a) -> live integration.
#40/#41 each displayed six successful checks; Issues #2-#10 remain open.
The existing [architecture specification](AUTHORITATIVE_ENGINE.md) now includes
component/lifecycle/sequence diagrams, model/API ownership/status, store/rollback
boundaries, mismatch register and test matrix. [Decisions](DECISIONS.md) replaces
stale clock/storage statements. No new engine implementation was introduced.

Verification recovered after the restricted execution profile changed: the
existing Python 3.13.15 .venv and npm.cmd work without dependency or security-policy
changes. Architecture checkpoint b6a420c passed **171 backend cases**, both
independent file verifiers, strict TypeScript/production build and **39 Playwright
cases**. All commands exited 0; no skipped tests. Actual OpenAPI 3.1.0 inspection
covered 73 schemas and all 30 Sandbox HTTP operations/operator dependencies.
The publication follow-up changes documentation only. GitHub fetch/auth work.
Architecture publication uses a narrow PR from feat/issue-2-architecture-alignment
to feat/live-sandbox-integration, preserving #40/#41/#43 and normal review gates.
Issue #2 remains open; no merge or teammate approval is claimed.

Issue #44 was reproduced with local synthetic trace records: unset/empty admin
configuration returned 200, and a malformed credential raised an exception. A
separate main-based [PR #45](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/45) on fix/44-agent-trace-authorization passed 97 backend and
33 browser cases; those are separate results, not added to the architecture count.
Review/integration of that fix is required before exposing privileged traces.
The original architecture head used the older Vite lockfile. This analysis integration retains #43's Vite 7.3.7 upgrade; its current scan is reported separately from historical architecture results. Upstream TestClient
deprecations and the existing optional-renderer chunk warning remain.

## Lifecycle integration

PR #39 extends #38 with local-only authorized archive/restore/delete, stale-confirmation protection, deletion tombstones, checksummed package recovery, schema-2 migration and trusted offline SQLite backup. Its exact merge state is available on [PR #39](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/39). Satvik explicitly waived the previous Vishwam review gate for #38/#39; no independent human approval is claimed. Normal repository checks remain required.

The earlier lifecycle integration verified 94 backend tests and 33 mixed browser/contract cases, including real FastAPI/SQLite import, replay, pass analysis, bookmarks, archive/restore, deletion and recovery. Strict TypeScript and production build passed. Final integrated-main results are recorded on the PR after merge; branch results alone do not certify main.

See [README](../README.md) and [CONTRACT](CONTRACT.md) for limits, permissions, migrations, packages and backup commands. Browser notes are local references, packages are datasets, and neither is an engine checkpoint. These are public-read synthetic datasets; a shared administrative token is not multi-user ownership isolation.

## Separate gates and dependencies

- #31 Blender assets retains its separate release/provenance review; #32/#33 preparation remains stacked separately. This data integration does not merge those branches.
- Diyan #2-#5/#7/#9 owns authoritative clock/state, complete RNG/pending queues, interventions, checkpoint continuation and experiment manifests. No competing engine or fabricated tracking is introduced.
- Mahir owns downstream evidence/AI integration. Hosted inference is guarded and unverified; no billable calls are required.
- Vishwam retains broader release/deployment responsibilities. Optional RTX/Unreal work #34 does not block the recorded-event product.

[The independent handoff](SATVIK_INDEPENDENT_HANDOFF.md) records the earlier feature integration and hardware evidence; its dated test counts are historical, not current totals.

## Satvik analysis integration branch

`feat/authoritative-analysis-integration` is stacked on Diyan's PR #41. It connects the existing scorer/evidence, event-derived metrics, local bookmarks, exports and optional 3D to owner-scoped committed runtime events. Short scenarios disclose the current adapter limit. It fixes redundant runtime selection clearing the authoritative view, distinguishes private bookmark sources, and updates the Vite development tool to 7.3.7 for the reported launch-editor advisories. No engine transition, snapshot schema, manifest algorithm or pending PR #31-#33 is replaced. Verification and review state are recorded on its focused PR; no merge or independent approval is assumed.
