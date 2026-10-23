# Release evidence ledger - 2026-10-23

This ledger separates evidence categories. Passing tests do not authorize cloud
spend, attest asset rights, or prove submission. Current verified main is
`0f45ca024bdcae294b74410023ff9533202416ed`, including merged #95, #96 and #97.
Its [exact-main run](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39911492834)
passed all six jobs; its backend log records 501 tests. No later candidate below
is described as merged main.

Historical PR #95 integrated main `1a2ff3727ebcd00a101f7b26d218588beaea620b`, with
[six passing exact-main CI jobs](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39901455301):
454 backend tests, 102 browser tests, four graphics-reporting tests, seven documentation tests, independent
manifest/experiment verification, pip consistency, frontend build/assets,
public read-only container smoke and offline Bicep compilation.

Historical baseline `07da294514f36820a7cf7d7c2dfacaab1adc735d` retains its
[own successful exact-main run](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39898162401).
The physical measurement source is clean
`e927785eb05f1dd09a9d4c20019c656f340a28d2`, not either merge SHA. Its probe and
evidence were subsequently integrated by #95; these are distinct provenance facts.

## Evidence and remaining acceptance

Open candidates retain separate reviews and exact-source evidence:

- [#98 graphics probe/evidence](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/98),
  publication `324aab83b935b7ad431a17ac8eb067a35575ce8c`: 13 report tests,
  eight documentation tests and a checkout-byte inventory contract. Two clean
  probe-`dc13f74` trials completed 902.544 and 902.503 seconds observed work;
  a separate integrated public-mode trial at `bbcce072` completed 902.233 seconds.
  Each recorded 177 samples, all profiles/cameras, nine inspected physical PNGs
  and no page errors/observed renderer changes. [Raw reports, source/build hashes and limits](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/blob/324aab83b935b7ad431a17ac8eb067a35575ce8c/docs/audit-evidence/graphics-rtx5070-clean-900-2026-10-23/README.md)
  retain both earlier failures and the diagnostic run separately. These bounded
  observations do not explain the prior closure, measure GPU execution FPS,
  establish leak absence or prove current-build Iris Xe compatibility. Final
  publication checks and independent review remain visible on the open PR.
- [#100 public operation budget](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/100),
  source `15f1ec2f752d9b017e194d4e7af4325b8f659437`: 506 backend and 104 browser tests locally;
  [source](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/40007388343)
  and [PR CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/40007398763)
  passed all six jobs. This is a process-wide budget, not per-IP fairness,
  distributed denial-of-service protection or a spend cap. Recap playback now
  respects Retry-After, retains truthful cutoffs and reports service failures
  separately; a single active judge can still exhaust the shared budget.
- [#101 observed agent execution and evidence gates](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/101),
  source `985520b4de4fbaf8dc641af197dc86ced3599f5c`: 525 backend tests locally;
  [source](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39946167218)
  and [PR CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39946173460)
  passed all six jobs. Pinned SDK compatibility is offline, not genuine hosted inference.
- [#102 provisioning preflight](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/102),
  source `6999cd1580639083b648db271573c83a3d911308`: 511 backend tests locally,
  including 68 provisioning/teardown cases. Failed or non-boolean group lookup
  output cannot authorize what-if, confirmation or provisioning.
  [Source](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/40002605831)
  and [PR CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/40002614400)
  passed all six jobs. Independent review and deployment acceptance remain pending.

The non-main source archive `bbcce072ab6f1100eb89cc88c958648d7605d617`
combines #98 through #102, including the recap-cooldown fix. Its
[exact-source CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/40008018221)
passed all six jobs: 541 backend, 104 browser and 13 graphics-report tests.
A separate real loopback public-mode browser check observed Retry-After 31,
zero requests during the cooldown, recovery/pause/generation, private write/trace
denials and a fixture WebSocket snapshot. This is HTTP/WS local acceptance,
not deployed HTTPS/WSS. No combined public PR was opened; the archive is not
main, an independent approval or a route around the focused PR reviews.
Earlier local integration `cc03d2ace465b7b1706a70bf7b797b0bcabbcce7` retains its
540-backend scoped result. Measured source commits are never replaced by a later
publication or documentation commit.

| Area | Established evidence | Remaining gate / disposition |
|---|---|---|
| Integrated source | #76 runtime analysis, #78/#79 replay/ForkCast fixes, #87 Fan Lens, #88/#92 Studio and backup, #89 trace envelope, #93 speech, #91/#94 deployment preparation and #95 graphics reporting/evidence are merged | This is integration evidence; it does not close their broader product acceptance |
| Historical local regression | Recorded before #95 merged: 454 backend and 102 browser tests, docs, seven assets, verifiers, pip check, disposable-DB release smoke; Python/npm audits found no known vulnerabilities in that audited dependency closure | Later candidates need their own checks and published CI; these are not fresh dependency-audit results for every commit |
| Integrated graphics evidence | Four failure-reporting regressions pass; physical production-GLB RTX probe passed on clean e927785, Chromium 156.0.8078.4, confirmed NVIDIA RTX 5070 D3D11 renderer; report and nine inspected screenshots merged through #95 | [Raw JSON and inspected screenshots](audit-evidence/graphics-rtx5070-2026-10-23/README.md). Three five-second samples/profile after warmup: about 165 RAF samples/s, 6.1 ms median / 6.2 ms p95. Browser pacing is not GPU execution FPS or the proposed 15-minute soak; matching-current-build Iris Xe acceptance remains pending |
| Historical physical Iris Xe with GLBs | [Raw report](benchmarks/iris-xe-glb-compatibility.json) at source 42feb9ea146b392590475ba27116c0a99533b331 records ANGLE Intel Iris Xe D3D11, driver 32.0.101.7088, headed Chromium 156.0.8078.4, four active v2 GLBs and zero page errors. [Method/limitations](ASSET_SECURITY_RELEASE_REVIEW.md#separate-physical-gpu-test-with-the-glb-kit-activated) accompany it | One five-second active sample/profile, about 59.7-60.0 RAF callbacks/s, median 16.7 ms and p95 17.0-17.1 ms, then 30 seconds idle. The active GLB hashes and manifest content are unchanged; its recorded manifest byte hash matches this Windows CRLF checkout (LF checkout bytes differ). Observer implementation has changed. Retain as historical physical GLB evidence, not a current-build/15-minute result, direct GPU timing or reviewed final compatibility acceptance |
| Azure #21 | Digest pinning, offline template and container checks, isolated fixture-only public mode, runbook | OPEN/blocked: no authorized resources or verified public HTTPS URL; zero GitHub environments at audit. Explicit cost approval, protected environment, actual OIDC minimum roles, #23 clearance, live HTTPS/WSS/restart and cleanup evidence required |
| Hosted AI #14/#15 | Provider integration and offline/scoped trace tests | Mahir: authorized real Microsoft model invocation and sanitized trace; mocks/configuration do not prove this. No billable call made by this audit |
| Legal/security #23 | Versioned manifest and documented controls; assets still pending-team-review | Vishwam/rights holders: attributable licensing, redistribution and release decision; test results cannot supply human authority |
| Submission #25 | Local app and smoke checks | Vishwam/authorized representative: real judge access, public video under 120 seconds, submission and confirmation |
| Physical graphics #34 | Recorded 2026-10-23 inventory: RTX 5070 Laptop GPU, driver 617.42, 8151 MiB VRAM; Intel Graphics also present. The published run confirms the selected NVIDIA RTX 5070 D3D11 renderer. A separate historical physical Iris Xe GLB report is linked above | Matching-current-build physical Iris Xe measurements, longer stability acceptance and human review remain pending. The earlier page-closure trigger is unproven; no RTX 5090 tested |
| Software / procedural graphics | Existing SwiftShader production-asset and older procedural Iris Xe artifacts retain original provenance and remain separate from both physical GLB reports | Neither is RTX 5070 evidence nor physical production-GLB Iris Xe acceptance. #13 Unreal NO-GO retained; optional work never blocks core submission |

## Closed engine issues: regression contract matrix

These are scoped code/test findings, not independent architecture approval or a
proof over all possible inputs. No engine, schema, RNG, fixture or golden hash was
changed. Keep #2/#3/#4/#5/#7/#9 closed unless a concrete failure invalidates them.

| Issue | Reviewed invariants / source | Existing regression evidence | Verdict |
|---|---|---|---|
| #2 | engine.py owns state; models.py versioned contracts; storage.py owner-filtered runtime DB; RuntimeRoom consumes revisions/cursors and retains token only in memory | test_runtime_integration.py, test_scenario_library.py, runtime browser journeys | PASS for exercised ownership/integration contracts; historical architecture tables are explicitly dated |
| #3 | build_scenario/initial_state/presets, canonical JSON, resolved roster/tactic validation and isolated deterministic RNG | test_authoritative_engine.py; scenario preset, invalid archive/config, stream isolation and round-trip tests in test_scenario_library.py | PASS for tested determinism, validation and compatibility; different seeds need not change every field |
| #4 | apply_command/advance lifecycle, ordered ticks, halftime/fulltime and terminal guards; persisted transactions rather than browser clock | test_authoritative_engine.py; crash-after-commit, process recovery, cancellation, worker concurrency and driver tests in test_runtime_integration.py | PASS for tested clock, continuation and transaction boundaries |
| #5 | models.py Tactics; engine.py validates identities and schedules interventions at current tick + 1; historical events are not rewritten | invalid tactics, fulltime legal events, future-only intervention and checkpoint-continuation cases in test_authoritative_engine.py | PASS for tested actor/policy invariants; normalized display coordinates are not measured metres |
| #7 | storage.py BEGIN IMMEDIATE, operation fingerprint/revision checks, owner scopes; accepted audit vs engine applied-state distinction | checkpoint retry/concurrency/rollback/process-death tests in test_checkpoint_metadata.py; runtime command/reconnect browser journeys | PASS for exercised authorization/idempotency/atomicity; no frontend authority introduced |
| #9 | manifest.py independently replays commands from resolved inputs; engine parse_json rejects ambiguous/nonfinite JSON; reproduction.py unsigned observational metadata | test_reproduction.py, bundle tampering tests, both committed CLI verifiers | PASS for tested corruption/version/size/ancestry and legacy compatibility; reproducibility does not authenticate author/host/time |

## Release order

1. Keep #21 open until actual deployment acceptance. Obtain explicit authorized
   subscription/region/spend scope; use [the existing deployment runbook](AZURE_DEMO_DEPLOYMENT.md)
   rather than creating a parallel infrastructure path. Its dated cost scenarios
   are estimates, not account quotes or a hard cap.
2. Collect Mahir's real hosted-model evidence and Vishwam's rights/release decision.
   Repository access or available secrets are not spending or release approval.
3. Verify judge access and the actual short video, then have the authorized
   representative submit and retain confirmation. Freeze the exact candidate SHA
   only after required gates, not merely because CI is green.
4. Continue optional graphics only within available time; use the
   [same bounded workload and artifact schema](GRAPHICS_BENCHMARK.md) for the
   physical Iris Xe handoff. Do not substitute software rendering or repeat Unreal.

Local Docker, Azure CLI and Bicep are unavailable at this audit; local commands
requiring them are NOT RUN. Passing CI compilation/container checks above are
separate from cloud deployment. No Azure resources, hosted inference, paid GPU,
video upload or submission was performed.
