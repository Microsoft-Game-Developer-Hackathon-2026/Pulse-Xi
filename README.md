# PULSE XI

[![verify](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/workflows/ci.yml)

**A synthetic football intelligence and tactical experimentation platform.**

A Microsoft Game Developer Hackathon 2026 project turning fictional football events into deterministic statistics, inspectable tactical explanations, synchronized broadcast cues and personalized recaps. The browser Sandbox Lab explores reproducible recorded fixtures. A separate authenticated authoritative engine is already available through backend APIs; its live Control Room and ForkCast integrations remain under review. All teams, players and events are synthetic. No Premier League feed, club logos, real-player tracking or broadcast footage is used.

## Application functionality

| Capability | Status and boundary |
|---|---|
| Synthetic fixtures | Three built-in seeded matches and validated custom seeds; reproducible on the same supported build |
| Replay | Play/pause, speed, seek, event stepping/filtering and selected-event pitch; versioned browser-local restoration of match/time/event, filters, speed, view, quality and analysis tab; restores paused |
| Analytics | Event-derived passes, shots, recoveries, pressure activity, networks, player summaries and windowed activity proxies |
| ProofTrail | Goal/tactical insights with supporting events and deterministic numerical verification |
| Pass Difficulty | Versioned 0–100 geometry heuristic with inspectable factors and player summaries; not a failure probability; pressure coverage unavailable |
| Sandbox Lab | Working fixture replay workspace; authoritative backend controls, checkpoints, branches and manifests are available through the authenticated API, pending frontend integration |
| 3D Observer | Lazy procedural pitch/stadium, five cameras, Low/Medium/High profiles, recorded-event evidence and 2D/WebGL fallback |
| Broadcast/FanDNA | Timed cue JSON/preview and five recap modes; limited English, Hindi and Spanish templates, not full interface translation |
| Match Data Hub | Searchable source-labelled library, authorized canonical JSON import, no-write preview, factual data-quality inspection, archive/restore/delete controls and checksummed portable match packages |
| Persistence | SQLite imported-event persistence and idempotent ingest; built-in/custom fixtures regenerate |
| Microsoft AI | Guarded optional provider code; verified local path uses deterministic fallback, not authenticated model inference |

The [authoritative engine integration guide](docs/AUTHORITATIVE_ENGINE.md) documents real backend controls, exact checkpoint continuation, isolated runtime branches, tactical interventions and independent manifest verification. The existing Sandbox UI still uses fixture replay. **Separate gates:** PR #31's editable Blender/GLB kit awaits Vishwam's asset/security approval; PRs #32/#33 remain separate. Higher-level ForkCast trial/comparison integration, calibrated prediction, public Azure deployment and real multi-agent inference are not supplied by the engine. See the [earlier handoff](docs/SATVIK_INDEPENDENT_HANDOFF.md).

## Availability on main and review-gated development

This documentation describes the source baseline `4d8a01e5e3483f6a4aafb62cd09def6fcfdd3713`, checked on 2026-10-21. A PR merged into another feature branch does not establish availability on main.

| Feature | Availability |
|---|---|
| Authoritative scenario/session APIs, bounded commands, checkpoints, isolated restore, interventions and manifest verification | Available on main; provisioned operator token required |
| Live Control Room, background progression, runtime observations, paired ForkCast and runtime analysis | Under review in [#53](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/53) |
| Native 60?5,400-second analysis and checkpoint/history/ForkCast acceptance controls | Under review in #57 and #59; sibling increments above #53 |
| Recorded Control vs Chaos / runtime Control vs Chaos | Under review in #42 / #58; runtime adapter also depends on #57 |
| Authenticated branch ProofTrail / request isolation correction | Under review in #51 / #54; existing recorded-insight ProofTrail remains available |
| FanDNA localization/accessibility expansion | Under review in #48; existing limited recap templates remain available |
| Additional Foundry command hardening | Under review in #52; trace authorization fix #45 is on main |
| Original Blender kit / compatibility correction | Under review in #31 / #60; rights approval remains required |
| Evidence-scoped agent tools / cost-gated validation / Broadcast Studio contract | Draft #55 / #56 / #50; not shipped features |
| Historical checkpoint/ForkCast preparation | #32/#33 are proposals, superseded in substantial part by executable engine work; not production contracts |

Validation branches and their benchmark reports are integration evidence, not releases. No hosted Foundry inference, public deployment or licensing clearance is claimed. [Current status](docs/PROJECT_STATUS.md) separates implementation from review.

## Windows quick start

Prerequisites: Git, a current WebGL-capable browser (3D optional), Python 3.11+ (CI uses 3.13), Node **20.19+ or 22.12+** (Vite requirement), npm and PowerShell. Verification used Python 3.13 and Node 24. From the repository root:

```powershell
git clone https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi.git
cd Pulse-Xi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\start.ps1
```

Startup installs backend requirements, runs `npm ci` when `node_modules` is absent, builds the frontend and starts FastAPI at **http://127.0.0.1:8000**. Sandbox: **http://127.0.0.1:8000/#/sandbox**. API docs: **http://127.0.0.1:8000/docs**. Read-only analysis needs no credentials, Blender, Unreal or paid service. Imports require a server-configured token (below). Stop with Ctrl+C. If port 8000 is occupied, use `.\scripts\start.ps1 -Port 8769` and open the corresponding URL; the default remains 8000.

After lockfile changes, run `npm ci` in `frontend` explicitly; startup does not reconcile an existing dependency directory. If activation is unavailable, use your configured interpreter directly rather than weakening system security policy.

### Manual development

```powershell
# Terminal 1, repository root
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --loop app.local_event_loop:create_loop --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2, repository root
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed by the command. Its API/WebSocket proxy targets port 8000. FastAPI serves `frontend/dist` after production build. Optional backend-only configuration is in [Foundry](docs/FOUNDRY.md); never put secrets in frontend variables. Keep hosted inference disabled without explicit authorization.

### macOS/Linux manual equivalent

From the cloned repository root (Python 3.13 and Node 24 match CI):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
(cd frontend && npm ci && npm run build)
python -m uvicorn app.main:app --loop app.local_event_loop:create_loop --app-dir backend --host 127.0.0.1 --port 8000
```

These are the same Python/npm entry points; local verification here used Windows, while CI executes on Ubuntu. For frontend development, run `npm run dev` from `frontend` in another terminal; its proxy expects backend port 8000.

## Configuration and trust boundaries

Set variables in the server shell before startup. Do not commit credentials or put them in frontend variables, URLs, logs or browser storage.

| Variable | Actual main behavior |
|---|---|
| `PULSE_RUNTIME_TOKEN` | Single operator bearer capability; at least 32 ASCII characters; unset/invalid configuration fails closed |
| `PULSE_RUNTIME_TOKENS` | Alternative JSON mapping of stable owner IDs to distinct tokens; takes precedence over the single-token configuration |
| `PULSE_RUNTIME_DB_PATH` | Separate durable engine database; defaults beside the match database as `pulse_runtime.sqlite` |
| `PULSE_DB_PATH` | Imported-match SQLite database; default `backend/data/pulse_xi.sqlite` |
| `PULSE_IMPORT_TOKEN` | Shared dataset write capability, at least 32 characters; not private multi-user ownership |
| `PULSE_ENABLE_LOCAL_DATA_ADMIN` | Exact value `1` enables additional direct-loopback administration checks; keep unset publicly |
| `PULSE_FOUNDRY_ADMIN_TOKEN` | Administrative capability for privileged agent operations; see security qualification below |
| `PULSE_ENABLE_FOUNDRY`, `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL` | Optional provider path; enabled only by exact `true` plus endpoint/model; leave disabled for offline work |
| `PULSE_BUILD_REVISION` | Optional truthful build revision in analysis exports; otherwise unavailable |

Generate a development secret server-side with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Operator tokens scope private runtime records to provisioned owners; inaccessible identities are concealed with 404. They do not create public signup or a collaborative permission model. Public recorded/imported matches have a different access boundary.

**Security qualification:** #52's command-credential hardening is not yet on main. Keep optional hosted agent execution disabled and do not expose privileged routes publicly while review is pending. CORS, localhost UI controls and a Host header alone are not authorization. Run development servers bound to loopback; this README does not certify public deployment.

## Backend architecture and API groups

```text
React / TypeScript recorded replay and analysis UI
    -> FastAPI
       +-- Recorded fixtures, imported-match analytics and evidence
       +-- Authoritative engine: scenarios, bounded commands, checkpoints, manifests
       +-- Optional Microsoft agent/provider integration (disabled by default)
       +-- Imported-match SQLite store (schema 2)
       +-- Separate runtime SQLite store
Browser profile: versioned local workspace, bookmarks and analyst notes
Local procedural scene: optional WebGL presentation, not a simulation clock
```

| API group on main | Entry points and boundary |
|---|---|
| Recorded matches | `/api/matches`, `/generate`, `/{match_id}/events`, `/state`, `/metrics`, `/tactics`; `/ws/matches/{match_id}` is replay transport |
| Data Hub | `/api/data-hub`, `/preview`, `/import`, `/recover`, `/matches/{match_id}/lifecycle`; mutations require server authorization |
| Analysis/evidence | Match pass difficulty, insights/evidence, recap, overlays and `/analysis-export` |
| Authoritative engine | `/api/sandbox/versions`, `/presets`, `/scenarios`, `/sessions`, session `/state`, `/snapshot`, `/commands`, `/events`, `/audit`, `/manifest` |
| Checkpoints/verification | `/api/sandbox/checkpoints/{checkpoint_id}`, `/restore`, `/api/sandbox/verify` |
| Optional agents | Insight explanation/agent-run and privileged `/api/agent-traces`; no cloud credentials needed for deterministic fallback |

Use `/docs` and `/openapi.json` for exact request models. [CONTRACT](docs/CONTRACT.md) covers recorded data; [AUTHORITATIVE_ENGINE](docs/AUTHORITATIVE_ENGINE.md) documents executable engine commands and authenticated examples. On main, `resume` permits bounded `advance` commands; it does not start a background wall-clock worker. There is no shipped live runtime UI or paired-experiment API yet.

### Reproducibility

Fixture seeds reproduce supported generator output on the same build. Engine manifests additionally identify resolved scenario, versions, input history and expected hashes. Checkpoints preserve complete runtime state, RNG and pending actions; imported dataset packages and browser workspaces are different artifacts. Independently verify the checked-in engine example from `backend`:

```powershell
python -m app.sandbox.verify_manifest ../docs/examples/sandbox/experiment.json
```

`verify_experiment` belongs to the unmerged runtime/ForkCast stack and is not a main command. Do not rescale native engine time to imply a 90-minute observation. Formula versions and source citations make calculations inspectable; neither synthetic outcomes nor heuristic difficulty scores are calibrated real-football predictions.

## Analysis workflow

1. Open Sandbox Lab and generate a replay with an integer seed from 0 to 2,147,483,647.
2. Play, pause, change speed and seek forward/backward; statistics follow the replay clock.
3. Filter recorded events and select a pass; inspect the path, difficulty factors and evidence.
4. Open ProofTrail to inspect supporting events; close with Escape.
5. Open 3D; choose Broadcast, Tactical, Isometric, Event focus or Free camera. Try quality profiles and reset.
6. Inspect source coordinates, return to 2D and continue replay.
7. Bookmark the selected event, save a note, then refresh: match, cutoff, selection and preferences restore in paused mode.
8. Search saved events, navigate back to a source event, or download JSON/CSV from Analysis exports. Filtered event downloads use the same timeline filters.

Replay controls view recorded events, not a running server simulation. Coordinates are normalized units, not measured metres. Markers represent sparse event locations; no continuous tracking, player speeds or ball trajectories are inferred.

## Match Data Hub

Open **MATCH DATA HUB** at **http://127.0.0.1:8000/#/data** to search built-in and SQLite-imported matches by title, identity or team. Cards show event counts and coverage. Expand metadata/data quality for categories, sequence consistency, missing identifiers and coordinate counts. These are factual completeness checks, not a predictive quality score. **Open for analysis** uses existing replay, Pass Difficulty, ProofTrail, bookmarks, persistence, exports and optional 3D event snapshots. Replay controls respect the declared match duration.

### Authorize imports locally

Imports and legacy ingestion **fail closed by default**. Before starting the server, configure a random token:

```powershell
$env:PULSE_IMPORT_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
.\scripts\start.ps1
```

Enter the same token into the Hub's password field. It is a server-wide write capability, not a user account. It stays in page memory and clears when leaving the Hub or refreshing. Tokens require at least 32 characters. Never place one in frontend environment variables, source files, URLs or localStorage. Remote operation requires HTTPS and explicitly authorized operators; unconfigured public installations cannot import. Host, Origin, CORS and hidden controls never grant permission. Imported matches remain readable by anyone who can access the server; there is no private multi-user data model.

### Import and portable packages

1. Select canonical JSON with `schema_version: "pulse-xi-match-package/1"` (legacy) or `"pulse-xi-match-package/2"` (checksummed), complete `match` metadata and an `events` array. Actual Match/MatchEvent schemas are exposed in `/docs`; see [CONTRACT](docs/CONTRACT.md).
2. **Validate and preview** checks schemas, references, boundaries and conflicts without creating a match or database. Review coverage, warnings and missing fields.
3. **Confirm import** commits one complete dataset transactionally. Identical reimports are no-ops; changed metadata/events conflict instead of partially overwriting existing records. Use a distinct identity for a different dataset.
4. Open the match for real analysis. Missing coordinates and identifiers remain unavailable.

Limits: **2,000,000 bytes per file/request**, **1,000 events per package/stored imported match**, **100 imported matches per installation**, 40 players per team and 32 levels of JSON nesting. Packages preserve event IDs, delivery sequences (including gaps), timestamps, qualifiers and metadata. IDs use 1..160 ASCII letters/digits plus `_ . : -`, starting with a letter/digit. Timezone timestamps, synthetic sources, distinct team/player IDs and six-digit hex team colors are required. Sequence order must agree with match time; tied timestamps are valid. Deletion is an explicitly authorized local operation; no bulk deletion or silent quota cleanup is provided. Archived matches still count toward the 100-match limit.

**Download complete package** includes all recorded events, regardless of replay cutoff. Export/import on a compatible installation preserves source data. Built-in/custom generated IDs are reserved: to import a separate copy, rename `match.match_id` and each event's `match_id` consistently in a newly authored version 1 package, or recompute a version 2 checksum. Never remove checksums merely to bypass a failed recovery validation. Unsupported/oversized output is rejected, never truncated. Supplied source/revision claims persist but are not authenticated; missing provenance stays unavailable. Export timestamps are real; engine hashes, checkpoints and experiment manifests are not invented.

Analysis JSON/CSV exports are **not** complete match packages. CSV import is unsupported because no lossless mapping exists for nested metadata. Package-imported matches cannot be changed through legacy append ingestion, preventing sequence rewrites from invalidating bookmarks. SQLite retains existing tables and transactionally retains `package_metadata` for provenance. Schema version 2 adds lifecycle and deletion records without replacing existing match/event tables.

### Dataset lifecycle and local security

Normal imports retain the existing token requirement. Archive, restore, delete and deleted-identity recovery additionally require **PULSE_ENABLE_LOCAL_DATA_ADMIN=1**, the same valid token, a direct loopback peer, and a localhost/loopback request URL. Forwarded/proxy headers and nonlocal clients are rejected. This explicit mode is only for trusted local administration: keep it unset in public or proxied deployments. No production multi-user destructive authorization model is implemented, and the shared token does not provide ownership isolation.

```powershell
$env:PULSE_IMPORT_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:PULSE_ENABLE_LOCAL_DATA_ADMIN = '1'
.\scripts\start.ps1
```

Use **Archive status** to inspect active, archived or all datasets. Archiving retains identity, events and provenance. Archived datasets disappear from normal match selection but **existing analysis links remain readable**; Open for analysis also works from archived cards. Restore reverses the archive flag. Built-in/generated fixtures cannot be changed by lifecycle operations.

**Delete imported match** opens a native keyboard-accessible confirmation dialog. Type the exact match ID. The server checks both its current generation and revision under a SQLite writer transaction, then removes events, provenance, lifecycle state and match metadata atomically. Stale confirmations cannot delete a recovered or changed dataset. A small deletion ledger retains match ID, deletion ID and time, blocking delayed imports from resurrecting deleted data. Capacity is 10,000 deleted identities; reaching it requires trusted offline maintenance rather than dropping safety records. Deletion is logical, not forensic disk erasure; existing backups are not removed.

Download a complete package before deletion. To recover, select that file and preview it; a deleted identity requires the separate **Confirm dataset recovery** action, current deletion ID and local administrator authorization. Recovery validates checksum and schema, creates a new dataset generation and restores source metadata/events/provenance in an active state. It does not claim to restore engine execution or RNG state. Conflicting live datasets are never overwritten. An interrupted read may finish from its consistent snapshot; new reads after deletion return 404.

Browser notes are not deleted with server data. **Check saved sources** verifies actual match endpoints (a generated match missing from the library is not presumed deleted). Retained notes can be downloaded as explicitly unverified references or individually removed after confirmation. Missing workspaces are preserved with an unavailable-source notice and reset/reload options. Same-origin tabs receive lifecycle notifications; no personal notes or tokens are broadcast. If BroadcastChannel is unavailable, refresh to recheck server state.

### Backups and recovery

Complete exports now use **pulse-xi-match-package/2**, requiring SHA-256 integrity metadata; existing version 1 imports remain supported. Checksum covers normalized typed schema_version/match/events/provenance, excluding integrity, with events sorted by source sequence. It detects corruption, not authorship: it is not a signature or engine manifest. Version 2 requires a compatible updated installation; older strict version 1 clients reject it safely.

For whole-database protection, use the trusted local CLI, not a web database upload. It uses SQLite's backup API to include committed WAL data consistently, verifies schema, integrity, foreign keys and payload identity, and writes only to **new** destination files. Keep backups outside public assets and protect them with operating-system permissions. No database-download or arbitrary SQLite-import API is exposed.

```powershell
# Repository root; create a private destination directory first.
New-Item -ItemType Directory -Path .local-backups -Force
$backupReport = python scripts/database-admin.py backup --destination .local-backups/library-backup.sqlite | ConvertFrom-Json
$backupReport
# Retain the SHA-256 printed in the JSON report. Stop the app before switching databases.
python scripts/database-admin.py restore --source .local-backups/library-backup.sqlite --destination .local-backups/recovered.sqlite --sha256 $backupReport.sha256
$env:PULSE_DB_PATH = (Resolve-Path .local-backups/recovered.sqlite).Path
.\scripts\start.ps1
```

Use only backups produced from your trusted installation. Review the reported source path and counts. If the running server uses a custom PULSE_DB_PATH, pass that exact absolute path with --source; relative server overrides are rejected when the CLI cannot determine its working directory unambiguously. Restore never overwrites existing files; it requires the recorded physical-file checksum and validates the copied database before reporting success. SQLite backups preserve archive state and deleted identities; restore rotates local administrative generations/deletion nonces to invalidate pre-restore forms; portable package recovery intentionally creates a new active generation. Legacy schema-1 backups migrate when the updated app opens them. Browser-local workspaces/notes and environment tokens are outside SQLite and are not included in database backups.

### Library performance evidence

On the available Windows/i7-1355U development machine (Python 3.13.14, SQLite 3.50.4), an isolated library of 100 imported synthetic matches / 37,700 generated events was queried three times through TestClient. The old path took 5,770 / 9,470 / 26,760 ms (median 9,470 ms); SQL aggregation in one read snapshot took 798 / 339 / 399 ms (median 399 ms, including migration on the first call). Response size changed from 280,684 to 289,963 bytes because lifecycle metadata is included. These are bounded local measurements under varying machine load, not a throughput SLA. Event models are no longer deserialized for library listing; a regression test enforces that boundary. No speculative database replacement, new index or pagination framework was added. A subsequent integration run on the same 100-match/37,700-event workload measured library median 967 ms (three samples), match lookup 40 ms, event retrieval 67 ms and package export 114 ms; single import/archive/restore/delete/recovery operations took 105/39/64/54/552 ms. This run overlapped browser verification and demonstrates load sensitivity rather than a stable 399 ms guarantee. The event query plan uses the existing match/sequence unique index.

## Durable analysis workflows

Workspace and bookmarks are local to this browser profile/origin, not authenticated accounts or engine checkpoints. No event feeds are stored locally. Workspaces use a versioned record (16,000-character read cap), autosave plus page-hide flushing, and source ID/sequence/time validation. Match/event changes, corrupt schemas, unavailable storage and cross-tab conflicts are reported with reset/recovery controls. An analysis link resolves current source events; after consuming it, refresh follows the saved workspace rather than repeatedly resetting to the old URL timestamp.

Bookmarks store match/event references, sequence/time and a note of up to 500 characters. The limit is 200 across all matches (256,000-character read cap). Save/update notes explicitly; unsaved typing is not retained. References are checked against actual events before navigation/export. Search/removal and confirmed reset work locally. Browser Web Locks serialize bookmark updates where available; older browsers fall back to read-before-write/last writer wins. Workspace changes from another tab do not move this tab automatically: reload the saved workspace or explicitly keep this tab. This is not multi-user synchronization.

Analysis exports support JSON and UTF-8 CSV: visible events, timeline-filtered events, selected pass/factors, existing match metrics, and source-validated bookmark references/notes. Backend exports reuse the scorer/metrics services, enforce match/cutoff, allow at most 5,000 source events and 8MB output, and never silently truncate. Narrow the cutoff when a limit is reached. CSV uses a UTF-8 BOM, standard quoting and formula-injection protection; nested values are JSON cells, nulls are empty cells and numeric zero stays zero. Empty CSVs have headers only; use JSON when empty-export metadata is needed.

JSON includes schema, real generation time, cutoff, source IDs, fixture seed and available formula version/units. Build revision is null unless backend `PULSE_BUILD_REVISION` is set; generator version/engine manifest are explicitly unavailable. Local notes are unverified analyst text, never evidence claims. Bookmarks after the cutoff or with missing/changed source events are omitted from export. Clearing browser data/private browsing/origin changes can remove local records; export references when needed. There is no cloud backup or history of multiple workspaces.

## Architecture and stack

```mermaid
flowchart LR
  S[Seeded fixture generator] --> E[Typed synthetic events]
  I[Validated batch ingest] --> DB[(SQLite)]
  DB --> E
  E --> A[Deterministic analytics and pass heuristic]
  A --> V[Evidence verification]
  E --> API[FastAPI REST and replay WebSocket]
  V --> API
  V --> C[Timed cues and fallback recaps]
  C --> API
  API --> UI[React replay and Sandbox Lab]
  UI --> D[2D pitch]
  UI --> O[Lazy R3F event observer]
```

Frontend: React 19, strict TypeScript, Vite, Tailwind/CSS, Three.js and React Three Fiber. Backend: Python, FastAPI, Pydantic and SQLite. pytest/Playwright exercise APIs and browsers. Calculations stay outside language models. The implemented authoritative engine owns state, clock and RNG; recorded replay only changes the inspection cutoff.

```text
backend/app/                  models, generator, analytics, evidence, APIs, storage
backend/tests/                API, determinism, persistence and scoring tests
frontend/src/features/passes/  pass inspector and typed responses
frontend/src/features/sandbox/ fixture setup, timeline, replay transport
frontend/src/features/observer/ lazy procedural 3D, cameras, evidence overlay
frontend/tests/               browser and transport regressions
scripts/                      Windows build/start and scoring benchmark
docs/                         contracts, methodology and handoff
.github/workflows/            backend/frontend/browser CI
```

## Testing

Dependency checks (from the repository root unless noted):

```powershell
python -m pip check
python -m pip_audit -r backend/requirements.txt --progress-spinner off
git diff --check
# frontend directory
npm audit
```

`pip_audit` is an optional development scanner (`python -m pip install pip-audit`), not a runtime dependency. At the documented main baseline, npm audit reports one high-severity direct Vite finding (locked 7.3.6); the compatible 7.3.7 correction exists in pending #53/#60. Do not treat a clean validation-branch scan as a clean main scan. Additional Python dependency hardening remains in #52.


```powershell
# Repository root
python -m pip install -r backend/requirements.txt
cd backend
python -m pytest tests -q -p no:cacheprovider
```

```powershell
# frontend directory
npm ci
npx playwright install chromium
npm run build
npm run test:e2e
```

`build` includes strict TypeScript. Playwright starts a real FastAPI server on port 8765; avoid an unrelated process using that port. CI uses software rendering for reproducibility, not physical GPU performance evidence. Final counts and measured limitations are in the handoff.

Asset validation (`python scripts/asset_contract.py`, `npm run validate:assets`) and `npm run test:contracts` belong to unmerged #31/#33 respectively; **they are not available on this main baseline**.

## Graphics pipeline and provenance

Main's observer is procedural and independently usable. Blender 5.2.2 authored an original editable source/GLB pipeline on PR #31, including manifest hashes, export tools and Khronos checks. Main also includes a renderer probe that supports procedural and asset-enabled scenes. It remains unmerged pending release review. Unreal #34 is optional offline authoring; neither tool is a browser runtime requirement. No mandatory CUDA, RTX, Pixel Streaming or cloud GPU is introduced.

The handoff records separate physical Iris Xe and software-renderer evidence; neither certifies RTX performance. Asset licenses and provenance are in PR #31's `assets/LICENSE.md` and `assets/manifest.json`, not yet main. No asset release approval is implied; third-party package licenses remain applicable.

### Repeat physical-GPU measurement

With the application running, use the frontend directory:

```powershell
$env:PULSE_GRAPHICS_HARDWARE='1'
$env:PULSE_GRAPHICS_URL='http://127.0.0.1:8000'
npm run measure:graphics
```

The headed browser rejects a detected software renderer, records renderer identity, active-orbit browser frame pacing and bounded interaction/heap observations in ignored `test-results/graphics/intel-hardware.json`. The filename is historical; inspect the renderer field to identify actual hardware. It does not certify GPU timer FPS or replace a longer physical-hardware test. Without hardware opt-in the probe uses headless Chromium. Keep the browser visible/unoccluded during measurement.

## Team and contributions

- Diyan: authoritative simulator, tactics, interventions, manifests; optional RTX work.
- Satvik: replay/frontend integrations, Pass Difficulty, observer, persistent analysis, bookmarks/exports, Data Hub and lifecycle; checkpoint/ForkCast consumers under review.
- Mahir: Microsoft AI, verified intelligence, personalization and broadcasts.
- Vishwam: release/security/provenance, deployment, broader QA and submission documentation.

Use focused branches/PRs with reproducible evidence. Do not push directly to main, force-push, overwrite teammates or close engine-dependent issues for preparation-only work. This is the current integration baseline; Vishwam retains final submission documentation/review ownership.

## Documentation

- [Current status](docs/PROJECT_STATUS.md)
- [Authoritative backend engine](docs/AUTHORITATIVE_ENGINE.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Local security boundary](docs/LOCAL_SECURITY_BOUNDARY.md)
- [Independent handoff and next integration sequence](docs/SATVIK_INDEPENDENT_HANDOFF.md)
- [API/event contract](docs/CONTRACT.md)
- [Pass methodology](docs/PASS_DIFFICULTY.md)
- [3D Observer](docs/3D_OBSERVER.md)
- [Optional Foundry path](docs/FOUNDRY.md)
- [Historical implementation audit](docs/SATVIK_IMPLEMENTATION.md)

## Troubleshooting

| Symptom | Action |
|---|---|
| Python import failure | Use the intended interpreter/venv; install `backend/requirements.txt` |
| Missing or stale Node modules | Run `npm ci` in `frontend`; check Node version |
| Port 8000 occupied | Use `.\scripts\start.ps1 -Port 8769`; Vite development proxy still targets 8000 unless explicitly configured. Do not terminate unknown processes |
| Playwright browser missing | From `frontend`, run `npx playwright install chromium` (Linux CI uses `--with-deps`) |
| Runtime returns 503 / 403 | Configure a valid server operator token / send the matching Bearer token; no browser runtime login exists on this main |
| SQLite cannot write | Check the configured database parent directory and OS permissions; preserve the original database before recovery |
| PowerShell activation blocked | Use `.\.venv\Scripts\python.exe` directly; do not weaken system execution policy |
| Backup destination exists | Choose a new destination; recovery intentionally never overwrites an existing database |
| Startup exits | Fix the first dependency/build error; startup stops on failures |
| Blank/failed 3D | Return to 2D, try Low, check WebGL2/hardware acceleration; replay remains independent |
| Blender not found | Main does not require Blender; authors on #31 can set `PULSE_BLENDER_PATH` |
| Missing asset/contract command | Utilities remain on the unmerged branches, not this main baseline |

### Limitations

Synthetic streams are simplified and not calibrated against real football outcomes. Full localization, advanced studio editing, authenticated Microsoft inference and Azure hosting are not established on this main baseline. Engine checkpoints and isolated branches are implemented; the live Control Room and paired ForkCast orchestration remain under review. A seed alone is not a full experiment manifest. The handoff identifies owners and exact integration gates.

Browser regression runs are bounded to two workers to avoid oversubscribing software-rendering contexts on developer laptops; explicit multi-tab and database race tests retain their own concurrency. Deep-link navigation hides stale controls until recorded-source restoration completes. No test retries or suppressed failures are used.

Local startup/test serving uses an explicit Uvicorn loop factory: Windows SelectorEventLoop avoids the observed Proactor socket-shutdown/reset race during request cancellation; Linux keeps Uvicorn auto/uvloop. This is a bounded local server (the Windows selector supports up to 512 sockets), not a high-concurrency public deployment configuration; the backend does not use asyncio subprocess APIs. Errors are not filtered or retried away.
