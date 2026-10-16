# Satvik development audit — 2026-10-16

## Scope and repository evidence

Repository: Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi. Starting combined branch: `prep/8-forkcast-comparison`, commit `a9768bf`; clean tree. Fetched main remains `888a2a9`. Read the six live issues, six PR descriptions/file lists/reviews, project specifications and implementation contracts. No human PR reviews or teammate engine branches were available. No AGENTS.md was present in the project/workspace paths checked.

Existing stack remains #28 → #29 → #30 → #31 → #32 → #33. Fixes were committed to owning branches and propagated through ordinary merges, preserving published history. No PR was merged, issue closed, branch deleted, main push, deployment or paid API call performed. The latest integrated code before this report is `26742f0`.

This is a bounded engineering audit of implemented local functionality, not a certification that every possible input, browser, security threat or hardware configuration is defect-free.

## Requirement-to-test inventory

| Issue / PR | Status | Implemented and verified | Remaining acceptance boundary |
|---|---|---|---|
| #27 / #28 | IMPLEMENTED — REVIEW REQUIRED | Versioned reduced-feature formula, missing locations, independent outcome, evidence recomputation/tampering, bounded list API, replay cutoff, player summaries, failure/retry UI | Future branch-scoped adapter requires the engine contracts. Pressure remains unavailable; no calibrated prediction claimed. |
| #10 / #29 | PARTIALLY COMPLETE | Real seeded fixtures, bounded/cancelled pagination, play/pause/seek, exact event selection/step, filters, pass-map inspection, generated-match proof, retry, saved custom replay, six viewport sizes, keyboard modal controls | Authoritative scenario wizard, engine controls, checkpoints, interventions and experiment workspace require #2–#9. |
| #11 / #30 | IMPLEMENTED READ-ONLY SLICE — REVIEW REQUIRED | Lazy event snapshots, coordinate/identity/time checks, cameras/reset, quality, reduced motion, context-loss/WebGL fallback, actual GLB integration on child branch | Modeled observer frames, continuous actor state and branch streams do not exist. Physical GPU benchmarking and other browser engines remain untested. |
| #12 / #31 | IMPLEMENTED — RELEASE REVIEW REQUIRED | Original sources/exports, hashes, measured size/triangle/primitive checks, binary bounds, source opening, browser loading/material clone and procedural fallback | Vishwam's #23 licensing/release approval remains pending. This audit reopened sources; it did not rerun the exporter or establish binary rebuild reproducibility. |
| #6 / #32 | BLOCKED; METADATA PREPARATION VERIFIED | Unknown-input validation, scope/version/boundary/provenance checks, valid UTC dates, typed UI states and real-engine test gates | No snapshot serializer, checkpoint endpoint, RNG/queue capture, isolated restore, exact continuation or seek benchmark is implemented. |
| #8 / #33 | BLOCKED; DISPLAY PREPARATION VERIFIED | Unknown-input consistency checks, branch/trial/hash metadata, units/deltas/ranges, explicit fixture labeling, responsive read-only comparison and production isolation | No real branch runner, intervention integration, paired trials, manifest verification or experiment API. Frontend consistency does not prove evidence exists. |

## Findings corrected

| ID / severity | Issue / component | Reproduction and root cause | Correction and verification |
|---|---|---|---|
| A01 / P2 | #27, main.py pass list/summary | Import a teamless pass, then query difficulty lists: HTTP 500. Generic events permit missing attribution; scorer requires valid players. | Controlled 422 without silently dropping records. New real-ingest/API regression first failed with 500, then passed. Formula unchanged. |
| A02 / P1 | #10, replayApi.ts | Supply malformed/null page, within-page duplicate ID/sequence or decreasing clock. The old reader casts JSON and checks only the preceding page cursor. | Runtime shape/coordinate/ordering checks, unique IDs, maximum page size and 100,000-event browser cap; explicit abort checks. Two transport regression cases failed against the original reader, then passed. |
| A03 / P2 | #10, App.tsx step | Select the recorded shot at 1000, then Next: goal at the same timestamp was skipped. Time-only navigation discarded event identity. | Step from selected event sequence, retaining same-second events. Real fixture browser test checks Next and Previous. Timestamp metrics still include every event at that timestamp. |
| A04 / P2 | #10, TacticalLab.tsx | Pass lines cannot be selected; shot circles cannot be activated with a keyboard. | Pointer/Enter/Space pass inspection and shot seeking. Real map selection synchronizes pitch, clock and inspector. |
| A05 / P2 | #10, proof drawer | Dialog has no initial focus, focus containment or Escape handler; requests can race. | Initial/contained/restored focus, Escape and cancellation of superseded/match-changed requests. Browser regression checks focus wrapping and restoration. |
| A06 / P2 | #10, style.css | 768px viewport has document width approximately 771px because the flex child retains intrinsic minimum width. | Allow main flex child to shrink; constrain narrow scoreboard content. Automated checks cover 1920, 1366, 1024, 768, 390 and 360px widths. Actual 768/360px screenshots were inspected. |
| A07 / P2 | #11, eventSnapshot.ts | Negative/fractional source clocks and invalid sequence/empty identity could be accepted by a direct observer adapter call. | Validate source clock/sequence/identity and match duration before rendering. Projection tests include invalid values and future/foreign events. |
| A08 / P2 | #12, asset_contract.py | Mutate actual GLB BIN length to zero or manifest source_bytes/draw_primitives. Old validator accepts them. | Validate BIN type/alignment/bounds, embedded buffer length/views and measured metadata. Three regressions first failed; all seven asset cases now pass. |
| A09 / P2 | #6, checkpointContract.ts | Null input throws; Date.parse normalizes February 31. | Accept unknown JSON and return diagnostics; strict UTC seconds/calendar validation. Three metadata cases pass, including malformed shapes and leap-day boundaries. No engine result claimed. |
| A10 / P2 | #8, comparisonContract.ts | Null nested input throws; unknown metrics/statuses, blank provenance, extra trial hashes, duplicate evidence and contradictory one-trial ranges can pass. | Shape and semantic guards plus bounded display inputs; development fixture cannot claim verified status. Regression first reproduced TypeError; five contract/browser cases pass. |
| A11 / P1 | #10, generated replay ProofTrail integration | Custom replay generates insight cards, but legacy global explain lookup searches only built-in/imported matches and returns 404. | Add match-scoped GET evidence with replay cutoff; keep legacy API. Backend and browser tests inspect custom-0 evidence and reject future/wrong-match requests. Shared evidence calculations untouched. |
| A12 / P2 | #10, generated match lookup | GET custom--1/custom-2147483648 accepts seeds rejected by generation; custom-00/custom-+1 returns a different canonical match identity. | Enforce canonical decimal seed ID and existing 0..2,147,483,647 bounds before generation. Backend boundary regression passes. |

## Fresh baseline and final validation

Environment: Windows 11 10.0.26300, Python 3.13.14, Node 24.12.0, Blender 5.2.2 LTS. Existing installed dependencies were used; no package changes were made in this audit.

Initial combined baseline: 27 backend tests, 22 Playwright application/API/metadata cases, four isolated comparison cases, strict production build all passed. These were rerun, not copied from the earlier report.

Final code verification commands:

| Working directory / command | Actual result | Scope |
|---|---|---|
| backend: `python -m pytest tests -q -p no:cacheprovider` | 33 passed, 6.81s final full run | Simulator/analytics/API/evidence, SQLite startup/recovery, pass scoring and new API/asset regressions |
| frontend: `npm run test:e2e` | 28 passed, 28.3s suite; strict build passed | Includes browser flows plus seven pure metadata/transport/observer cases and a production-route API check; not 28 independent rendered journeys |
| frontend: `npm run test:contracts` | Five passed in the post-fix run; rerun after final merge | Separate strict contract TypeScript check and development-only comparison harness |
| root: `python scripts/asset_contract.py` | All three assets valid | Container/hash/provenance/budget checks; seven asset pytest cases included above |
| frontend: `npm audit --omit=dev --json` | Zero reported production dependency vulnerabilities | Registry advisory check of current combined lockfile, not a complete dependency/security audit |

Critical replay, context-loss and asset tests passed in multiple full branch/integration runs. No retries, disabled assertions or test deletions were used to obtain passing results. No separate lint/formatter script is configured.

## Actual browser and bounded reliability probes

- Six requested viewport sizes tested for document overflow and visible controls, with screenshots generated. The new viewport test monitors page runtime errors. Actual narrow/tablet and original-GLB screenshots were visually inspected.
- Separate real-backend Chromium journey on port 8767: generated seed 4411, opened proof, three 3D mount/camera/quality cycles, twelve rapid seeks, then 2D recovery. No page/console errors or HTTP >=400 responses. Renderer chunk and each of three GLBs requested once. This is bounded reliability evidence, not a long-duration leak or load certification.
- Original-asset standard scene: 9 draw calls, 1,216 triangles, 9 geometries; low mode: 8 calls, 1,168 triangles, 8 geometries. Repeated standard mounts returned to the same geometry count. Isolated first-ready samples 509.9/414.8/345.3ms; concurrent suite samples can exceed 1s. SwiftShader timing is not physical GPU FPS.
- Separate temporary SQLite probe: mixed new/conflicting batch rolls back, 16 duplicate ingests over eight workers stay idempotent, integrity_check returns ok. Untrusted CORS preflight rejected; tested asset traversal and development-preview paths return 404. Initial probe cleanup failed because the probe itself retained a SQLite handle; after closing that handle explicitly, the entire probe exited successfully. Production storage already closes connections.
- Blender opened all three editable source files; polygon counts 460/80/102 match manifest and no external image files were referenced. Source files/GLBs were not modified.
- Current tracked text, Git history and two production JS bundles were checked for GitHub-token/private-key patterns; no matches or tracked .env found. This narrow pattern scan cannot prove absence of every secret type.
- Windows Proactor occasionally logs connection-reset callbacks during deliberate request cancellation; browser cancellation assertions pass. This OS/server transport message was not suppressed.

## Performance

Final build: default JS 277.72kB / 86.39kB gzip; optional renderer 956.00kB / 258.94kB gzip; CSS 30.74kB / 7.91kB gzip. The optional chunk warning remains visible. Default 2D tests verify no renderer download. Original GLBs still total 96,116 bytes.

Thirty warm TestClient pass-list requests: 148 packets, 228,088 response bytes, median 22.280ms / p95 37.305ms, measured while other audit/build work was running. This is not a controlled comparison with older timings or a cloud SLA. No demonstrated bottleneck justified an optimization rewrite; none was attempted.

## Remaining gates, ownership and limitations

1. **P1, blocked:** authoritative snapshot/RNG/queue/clock/session contracts from Diyan (#3–#5), interventions #7 and manifests #9. Checkpoint and ForkCast execution acceptance remains unmet. No substitute engine, fabricated branch result or future-state data was added.
2. **P1, public release gate:** shared ingest remains a local unauthenticated mutation API with no total per-session storage/rate quota. Public deployment needs Vishwam's #23/#21 authorization/resource-bound design. CORS is not authentication. This audit did not change shared product security architecture or claim a public security clearance.
3. **P2, integration boundary:** event streams have no server revision token across pagination. Client validation catches duplicates/order errors but cannot prove that all pages came from one transaction during concurrent out-of-order ingest. An authoritative immutable stream/revision contract is needed before shared live use.
4. **P2, untested environments:** no Firefox/WebKit, real screen-reader session, exhaustive contrast audit, physical GPU FPS, long-duration heap soak, full Khronos conformance or hostile multi-user cloud test. Keyboard/mobile checks passed; comprehensive accessibility certification is not claimed.
5. **Release review:** PRs remain open; #29/#32/#33 remain drafts where engine acceptance is incomplete. Original asset release_approval remains pending-team-review. No Foundry inference, Azure deployment, actual checkpoint continuation or experiment run was attempted or claimed.

## Review and local demonstration

Review PRs in stack order: [#28](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/28), [#29](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/29), [#30](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/30), [#31](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/31), [#32](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/32), [#33](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/33). Latest GitHub checks must be read from those heads; old successful runs do not establish a later head's status.

Run `./scripts/start.ps1` at repository root, then open `http://127.0.0.1:8000/#/sandbox`. Existing manual backend/Vite commands remain unchanged. No new environment variable or credential is needed. Generate a seed, play/pause/seek, select a timeline/map pass, inspect its formula/evidence, open custom-match proof, switch to 3D/cameras/quality and return to 2D. Save/restore/intervene/fork controls remain unavailable until the real engine integration exists.

Next priorities: independent review of #28/#30/#31; agree Diyan's versioned engine/session contracts; implement and prove #6 before real #8 integration. Keep public deployment behind #23 security/provenance review. No cost approval is needed for these local tests; genuine hosted inference and cloud provisioning still require explicit approval.
