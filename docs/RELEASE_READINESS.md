# Local release evidence and remaining submission gates

## Current audit addendum - 2026-10-22

Main `d19a898` has merged native analysis, recorded Control vs Chaos, FanDNA,
branch ProofTrail/request isolation, Atelier UI, agent tools and the Foundry
validation pathway. Earlier snapshots below retain their original provenance;
statements that these PRs were pending describe those earlier revisions only.
Provider installation/offline validation is not a hosted model run. Runtime
Control vs Chaos PR #76 remains conflicting and unreviewed at inspection.

See [requirements](FINAL_REQUIREMENTS_AUDIT.md), [measured performance](PERFORMANCE_AUDIT.md)
and [current readiness](FINAL_HACKATHON_READINESS_REPORT.md). Registration was
confirmed by the user; the final public video, clean-browser judge access,
rights/release decision (#23) and submission confirmation (#25) remain unverified.
No deployment, paid inference, upload or submission was performed.


Audit date: 2026-10-21 UTC (2026-10-22 India). Starting main:
`c5a93f46a24fa857318f237f37f9184a4b4d90dc`,
[successful baseline CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39664390354).
This report describes the release-verification change built on that commit. The
PR and its Actions runs identify the final tested/merged revision; do not interpret
the starting SHA as a freeze of later main. No public deployment, live paid model
invocation, video recording or submission upload was performed in this audit.

## Findings and risk-weighted test map

| Priority / classification | Behavior / evidence | Release disposition |
|---|---|---|
| Critical / already satisfied | Engine clock/order/actors/goals/terminal state, fixed-seed hashes, checkpoints and golden continuation: `test_authoritative_engine.py` | Full backend regression required on each release revision |
| Critical / already satisfied | Command revisions, duplicate receipts, concurrent writes, rollback/process death, branch isolation: authoritative, runtime integration and checkpoint metadata tests | No change to hashed engine, event, checkpoint bytes or goldens |
| High / reproduced defect | SQLite NULL text primary key bypassed checkpoint metadata joins while row count and FK checks passed | `backup.validate_database` now requires complete joined coverage; `test_backup_rejects_detached_checkpoint_metadata` failed before fix and passes after |
| High / already satisfied | Operator/private ownership, foreign-resource 404, cursor/reconnect/revocation and error no-store: runtime integration, scenario library, runtime analysis tests | Provisioned capabilities, not public user accounts |
| High / reproduced defect | `GET /api/agent-traces` omitted cache restrictions on admin success/error | Explicit no-store for 200/403/503; new release security test failed before fix; no actual proxy leak or credential exposure demonstrated |
| High / missing test, now covered | Every registered runtime REST operation must reject missing credentials before resource access | `test_release_security.py` checks dependency presence, actual 403 and no-store across all runtime REST operations; existing WebSocket tests cover first-frame auth and rotation |
| High / already satisfied | Malformed/duplicate/nonfinite/deep/oversized JSON, unsafe Windows paths/Host, schema versions, manifest tamper/first divergence | Security boundary, scenario library, reproduction and runtime tests; size errors 413, ambiguous JSON 400, malformed/schema errors 422 |
| High / missing test, now covered | Allowed CORS origin must not grant runtime access | Release CORS preflight/actual unauthorized-request regression; origin allowlist remains two local Vite origins |
| High / defense in depth | Browser harness could inherit enabled Foundry settings from caller | Harness explicitly disables Foundry and clears endpoint/model/admin configuration; no hosted calls required |
| High / reproduced harness defect | Backend tests inherited configured provider/admin state and could start TestClient drivers against developer paths | An existing unconfigured-provider test failed under fake inherited configuration; autouse baseline now clears app settings, disables drivers/providers and assigns per-test stores. The complete 297-test suite passes under deliberately inherited fake settings; its sentinel database was not created. Explicit configuration tests still provision their own values |
| Normal / documentation gap | Windows build helper selected `npm.ps1`; README called integrated runtime proposed, schema 3 current and engine ownership future | Helper uses `npm.cmd`; README corrected without changing execution policy |
| Normal / already satisfied | Real scenario library, archive roundtrip, checkpoint UTC, interventions, evidence, run recovery, comparison, asset fallback, keyboard/mobile/viewport | 66 real Playwright tests; largest history case runs after ordinary cases to avoid CPU-contention failures; no skips/retries added |
| High / not verifiable | Public HTTPS, gateway limits, production durability, live model/provider failure behavior and final submission | Separate #14/#15/#21/#25 gates; local tests do not satisfy these |
| High / external approval required | Asset author/CC0 authority and root application/helper license decisions | #12 is technically complete/closed; #23 remains open; technical validation cannot authorize distribution |

The risk priorities describe what release validation should protect; they are not
claims that a high-severity exploit was reproduced. No complete penetration test,
external accessibility certification or real-football accuracy validation occurred.

## Commands and actual local results

Windows 11 build 26300, Intel64 Family 6 Model 198, Python **3.13.15**,
Node **24.21.0**, npm **11.19.0**, Chromium via Playwright. A new clean Git
worktree and new temporary Python venv were used; the original checkout, venv,
databases and other worktrees were preserved. Python direct pins came from
`backend/requirements.txt`; transitive versions are in the inventory snapshot.

| Command (working directory) | Result |
|---|---|
| `python -m pip install -r backend/requirements.txt` (root, fresh venv) | Succeeded; 29 installed distributions including pip |
| `npm.cmd ci --registry=https://registry.yarnpkg.com --no-audit` (frontend) | Succeeded, 110 installed packages; unchanged lockfile |
| `python -m pytest tests -q -p no:cacheprovider` (backend) | Initial baseline: 293 passed; release: **297 passed** in 35.80 seconds; final inherited-configuration probe **297 passed** in 36.04 seconds, one TestClient deprecation warning |
| `python -m app.sandbox.verify_manifest ../docs/examples/sandbox/experiment.json` (backend) | Exit 0, verified true |
| `python -m app.sandbox.verify_experiment ../docs/examples/sandbox/forkcast.json` (backend) | Exit 0, verified true |
| `npm.cmd run test:e2e` (frontend) | Baseline **66 passed** in 2.3 minutes; final publication rerun **66 passed** in 2.5 minutes; includes strict `tsc -b` and production Vite build |
| `python scripts/release-smoke.py` (root, built frontend) | Actual isolated Uvicorn + HTTP journey, restored child, real intervention/audit, completed paired trial, two independent CLI verifications; exit 0 |
| `python -m pip check` | No broken requirements |
| `python scripts/asset_contract.py` / `npm.cmd run validate:assets` | All 7 assets valid; 0 validator errors/warnings; informational unused UV entries retained |
| `python scripts/collect-runtime-notices.py --check` | 23 runtime package instances match retained notices |
| `npm.cmd audit --json --registry=https://registry.yarnpkg.com --fetch-retries=0 --fetch-timeout=15000` | 181-package dependency graph; 0 known advisories |
| `python -m pip_audit --path <fresh-venv-site-packages> --format=json --progress-spinner=off` (separate audit-tool venv) | 29 distributions, 0 known advisories |
| `python scripts/release-inventory.py` | Actual generated OpenAPI/access inventory, installed Python declarations, Node lock licenses, limited tracked-source/built-JS secret-pattern scan |

The registry override was needed because this machine's official npm registry
certificate chain is untrusted. No TLS verification, execution policy, lockfile
or machine-wide registry setting was weakened. esbuild's install-script allowlist
warning remains; actual build succeeds. The lazy Three.js chunk is about 984 kB
and Vite warns above 500 kB; this audit does not suppress that warning. FastAPI's
TestClient emits an httpx deprecation warning; no assertions were weakened.

Failed diagnostic commands are not counted as passes: running the newly added
corruption/cache regressions before their fixes failed as intended; one asset npm
command from the repository root failed with ENOENT and was rerun successfully
from `frontend`; redirecting the Windows startup helper's native stderr under
PowerShell 5.1 `Stop` produced a NativeCommandError from pip output. The normal
interactive helper then started successfully, and actual `/health`, `/` and
`/openapi.json` returned 200 (64 OpenAPI paths / 68 HTTP operations). No security
policy change was used to resolve these diagnostics.

### Measured local performance

Commands: `python scripts/sandbox-benchmark.py --samples 5` and
`python scripts/benchmark-runtime-acceptance.py --iterations 3` (root).
Raw JSON is retained under [release evidence](release-evidence/). Runs overlapped
other verification; variation is reported, not hidden or turned into CI timing assertions.

| Workload | Samples | Measured result |
|---|---:|---|
| Resolved scenario construction/hash, default / maximal names/attributes | 1,000 each | Median 0.0521 / 0.0542 ms; p95 0.0576 / 0.0595 ms |
| 4 presets × 5 fixed seeds, full 5,400-tick simulation | 20 | 0.0866–0.1590 seconds; canonical event hashes in raw report |
| Checkpoint save / restore at tick 0 | 3 each | Median 7.070 / 5.514 ms; 5,957 snapshot bytes |
| Checkpoint save / restore at tick 2,700 | 3 each | Median 30.532 / 29.634 ms; save max **650.393 ms**, 198,410 bytes |
| Checkpoint save / restore at tick 5,400 | 3 each | Median 53.065 / 58.987 ms; 389,573 bytes |
| Read-only replay to tick 5,399 | 3 | Median 125.051 ms, max 125.470 ms |
| Paired 1 / 3-trial experiments, horizon 120 | 3 each | Median 180.819 / 845.669 ms; max 204.713 / 1,796.423 ms |
| Experiment traced peak Python allocations, 1 / 3 pairs | 3 each | 251,977 / 2,167,508 bytes; **not process RSS** |
| Tactical HTTP acknowledgement / next tick (warm TestClient) | 20 each | Median 24.838 / 21.636 ms; max 66.557 / 24.014 ms |
| Runtime manifest verification | 5 | Median 413.710 ms, max 432.928 ms; 85,398-byte input |
| Fresh server health / first scenario create (cold empty runtime schema migration included) | 1 illustrative run | 765.61 / 27.55 ms; full real-HTTP smoke 4.54 seconds |

Storage timings are in-process, with local SQLite WAL; experiment measurements
include tracemalloc overhead. Health readiness does not prove database readiness;
the separately measured first create opens/migrates the empty runtime store.
Browser baseline took 2.3 minutes including the heavy 5-pair/600-tick archive case.
These workstation results establish reproducible workloads, **not production SLAs**.

## Endpoint, dependency and provenance inventory

[inventory.json](release-evidence/inventory.json) is generated by
`scripts/release-inventory.py` after requirements installation and `npm ci`.
It lists every OpenAPI HTTP operation, actual dependency functions, response
schema references and access classification, plus two WebSocket transports.
Declared OpenAPI statuses do not enumerate every middleware error.

| Surface | Access / actual failure family | Supporting tests |
|---|---|---|
| Health, static UI, recorded match/data-hub reads, analysis, recap and deterministic explanation | Public synthetic library; bad identifiers/cutoffs 404/422; generate creates only bounded cached synthetic fixtures | simulation, data hub, analysis export, pass difficulty, security boundary |
| Ingest, package preview/import | Shared bearer import capability; unset/wrong 403; conflicts 409; size 413; schema 422 | data hub + storage tests |
| Data lifecycle/recovery | Import token **and** opt-in direct-loopback administration; forwarded/proxied requests denied 403 | library lifecycle/startup tests |
| Trace inspection | X-Admin-Token; unset 503, wrong/malformed 403; all results no-store | security boundary + release security |
| Agent-run | Enabled provider **and** current admin capability; unconfigured 503, unauthorized 403, dependency 503, provider failure 502 | Foundry command auth tests mock only the provider boundary; no real call |
| All `/api/sandbox` REST operations | Owner bearer; unconfigured 503, bad auth 403, foreign/absent 404, conflicts/cursors 409, capacity 429, validation 422; no-store | route-wide release guard and resource-specific tests |
| Runtime observer WS | Origin check; token in first JSON frame (5 s / 4,096 chars), recheck/revocation, initial snapshot and cursor deltas; rejection closes 1008 | runtime integration WS tests |
| Recorded replay WS | Public synthetic event playback; not authoritative simulation state | simulation/browser tests |

Node's 181 lockfile package entries have declared licenses; runtime notices cover
23 installed package instances (a different count/scope). All 29 installed Python
distributions have a license declaration/classifier; inventories are **declarations**,
not legal advice or proof of ownership. Optional Foundry SDK environment is outside
this base-environment audit. Dependency advisories can change after this scan.

Seven Blender source/output pairs match the committed manifest hashes and budgets.
The author declares project-created procedural artwork under CC0; offline Blender
generators have separate GPL-3.0-or-later declarations. Runtime MIT/ISC/BSD notices
and the Khronos development license are retained. See [asset review](ASSET_SECURITY_RELEASE_REVIEW.md),
[license inventory](../licenses/README.md) and [creative no-use record](CREATIVE_ASSETS.md).
`assets/manifest.json` still says **pending-team-review**. The application has no
root license; rights holders must resolve application/helper scope and author/CC0
authority. No Premier League footage, real teams, likenesses, music or new media
was imported by this release change.

The bundled scan checks tracked UTF-8/text files and built JavaScript for AWS key
IDs, GitHub token patterns and private-key headers, reporting only file/line.
It is not an entropy scan, full Git-history scan, license-compatibility opinion
or penetration test. A separate **detect-secrets 1.5.0** scan subsequently ran with
`scan --no-verify` on tracked source, and `scan --no-verify --all-files frontend/dist`
on the build. No credential validation/network probes were attempted. Source had
93 entropy findings: inspected asset/commit/config/state/event digests, reproducible
RNG keys and sample runtime API paths; no credential was identified. Built output
had zero findings. [Triage](release-evidence/secret-scan-triage.json) records categories;
raw hashed-finding outputs remain in the temporary evidence directory as
`pulse-release-secret-scan.json` and `pulse-release-bundle-scan.json`.
Gitleaks/Trivy and a full Git-history scan were not run.
No scan result authorizes committing a credential or certifies absence of secrets.

License obligations also include CC-BY-4.0 `caniuse-lite` and MPL-2.0 `lightningcss`
in the development lock graph, Python certifi's MPL-2.0 declaration, and PSF-2.0
typing extensions. These are distinct from the installed browser runtime notices;
retain the relevant texts/attribution when redistributing the corresponding tools
or sources. No AGPL dependency is declared in this inventory. This is not a legal
compatibility clearance or a license grant for the application's own code.

## Threat register and remaining release decisions

| Finding / boundary | Mitigation / remaining risk | Dependency / decision |
|---|---|---|
| Backup accepted detached metadata (reproduced local integrity defect) | Fixed joined coverage check; no migration or engine hash change; trusted offline DB tooling only | New corruption regression plus existing backup/reopen tests |
| Trace caching policy absent (reproduced response defect) | Explicit no-store on success/error, existing constant-time auth unchanged | No credential leak or public proxy exploit demonstrated |
| Runtime owner capabilities | Fail closed, owner-keyed SQL, foreign 404, no-store, bounded commands and transactions | Provisioning/rotation/HTTPS and logs still deployment operator responsibilities |
| Public compute/WS abuse | Body/depth/event/trial caps and bounded DB capacities exist; no gateway rate quota, per-owner fair scheduler, retention cleanup or slow-client SLA | #21 must define exposure, gateway timeouts/rate limits and durable storage before public release |
| Optional model prompt/output risk | Evidence allowlist, deterministic audit and truthful fallback; secrets backend-only; ordinary tests disable paid path | #14/#15 need actual approved credential/cost smoke, timeout/cancellation/tool review; open PRs #55/#56 are not main |
| Dependency supply chain | Exact Node integrity lock, direct Python pins, retained declared licenses and fresh advisory scans | Python transitives are not fully locked; retain actual inventory per candidate; optional SDK scan still separate |
| Asset/application rights | Technical hashes/notices verified; procedural/CSS/SVG fallback exists | #23 rights holder confirmation and root/helper license decision; **not approved by this audit** |
| Submission/deployment claims | Offline/local evidence only; no fabricated provider/deployment/video | #21 public demo, #25 actual capture/upload and authorized representative submission |

Issues #16/#17 and PRs #51/#54/#50 remain separate proposed sandbox ProofTrail/
broadcast work; the existing deterministic insight evidence/overlay templates are
implemented. The unrelated UI redesign PR #71 was not absorbed. Future integration
must rerun this matrix rather than inherit this candidate's green checks.

## Reproducible local setup and recovery

Use [README quick start](../README.md#quick-start) and [Live Sandbox](LIVE_SANDBOX.md)
as canonical configuration/API guides. For policy-restricted Windows, activation
is optional: invoke `.venv\Scripts\python.exe` directly and prepend its Scripts
directory to process PATH when using the PowerShell helper or browser suite.
Never relax machine execution/TLS policy. `.env.example` is a template; the helper
does **not** automatically load `.env`. Set variables in the server shell.

Use unique temporary paths for `PULSE_DB_PATH` and `PULSE_RUNTIME_DB_PATH` for tests;
never point destructive/migration probes at a personal database. The default
read-only fixture UI does not require an operator credential. Provision a fresh
server-side operator token for the live Control Room and paste it only into its
in-memory credential field. Do not put it in a URL, screenshot, export or bundle.

After building, `python scripts/release-smoke.py` starts its own loopback server,
uses ephemeral credentials/temporary databases, validates the supported end-to-end
journey, verifies two real exports using separate CLI processes, stops that server
and removes only its own disposable files. CI runs the same script after browser tests.
It never contacts Foundry/Azure or reuses a developer database. The Windows helper
was also started independently and served health, HTML and generated OpenAPI.

Back up imported-match and runtime stores **separately** using
`python scripts/database-admin.py backup --source <library-path> --destination <new-backup>`
from the root, and `python -m app.sandbox.backup backup <runtime-path> <new-backup>`
from `backend`; see [architecture](AUTHORITATIVE_ENGINE.md)
and [live guide](LIVE_SANDBOX.md). Stop writes for a coordinated two-store backup:
there is no cross-file transaction. Restore to a new path with the saved checksum;
never overwrite an existing DB. Schema rollback means restore a compatible backup
with its matching build, not an automatic down-migration. Runtime schema is 4;
imported-match schema is 2. Legacy unknown UTC remains null. Ctrl+C stops local
startup; do not delete a user's databases to reset a session. Reset creates a new
session; restoring checkpoints creates an isolated branch rather than editing history.

Windows fresh install/start, actual HTTP journey and browser tests were executed.
Ubuntu CI supplies clean requirements/npm installation and the same HTTP journey;
its exact final run must be checked before claiming that revision passed Linux.
macOS interactive setup and a production container/public network were not tested.
