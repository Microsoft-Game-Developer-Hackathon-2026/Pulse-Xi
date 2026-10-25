# Pulse-Xi — submission packet

Paste-ready text for the hackathon project form, the reviewer guide and the recording
storyboard. Everything below was checked against the merged code on 2026-10-25; items that
are prepared but not done are labelled as such. Rules source:
[OFFICIAL RULES.md](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md)
(re-read 2026-10-25, unchanged since 2026-10-24; deadline **October 27, 2026, 11:59 PM Pacific** = October 28, 12:29 PM IST).

**Tagline:** Synthetic football intelligence, with evidence behind every story.

## Elevator pitch (form field)

Pulse-Xi turns synthetic football events into explainable match intelligence. Every moment links
to the source events behind it and is framed three ways from the same facts: tactical analyst, fan
(English, Spanish, Hindi) and broadcast director. A deterministic engine lets analysts checkpoint a
match, change a tactic, run paired ForkCast experiments and verify the result independently. All
facts come from the engine; stories are rule-based, with an optional Microsoft Agent Framework /
Foundry path that is verified offline only. Source: github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi

## Full description (form field)

**Problem.** Football dashboards report outcomes; fans want to know why a moment mattered,
analysts want the calculation, broadcasters want concise timed output, and nobody can tell
generated prose from evidence.

**What it does** (all in the merged app, local run):

1. *Ingest and interpret.* A seeded synthetic generator and a validated import path produce
   events (passes, shots, goals, recoveries, pressure). Statistics, tactical windows, Control vs
   Chaos and a heuristic Pass Difficulty are computed from those events only.
2. *Explain.* Verified rule-based insights cite exact event IDs; ProofTrail shows the calculation and
   source events. **One Moment · Three Stories** shows the analyst, fan and director framing of one
   insight side by side with a computed check that all three cite the same source events; the
   director cue is labelled PROPOSED until a producer approves it in Director Studio.
3. *Render.* Timed lower-third cues export as versioned JSON; a highlight manifest drives a reel
   player and WebM renderer built only from event data (no footage).
4. *Personalize.* Five audience modes and three languages change wording and depth, never facts;
   optional on-device speech reads the recap.
5. *Experiment.* An authoritative deterministic engine (seeded clock/RNG, halftime, terminal state)
   supports checkpoints, restore as a new branch, future tactical interventions, paired ForkCast
   trials and two independent verifier CLIs.

**Honest limits.** Data is synthetic and uncalibrated; no tracking, speeds or ball trajectories are
inferred; narratives are templates, not model output; no hosted inference was run.

## Microsoft / Azure technology inventory (verified status)

| Technology | Status | Evidence |
|---|---|---|
| Microsoft Agent Framework (`agent-framework-foundry` 1.13.0, `agent-framework-orchestrations` 1.3.1) | **Optional; offline-verified, not run against a hosted model.** Staged Analyst → Story Editor → Evidence Auditor → Director → Fan workflow, tool allowlists and observed-stage traces are tested with fakes | `backend/app/agents.py`, `agent_tools.py`, `test_agent_tools.py`, `test_agent_execution_trace.py`, issue #15 |
| Microsoft Foundry | **Adapter and fail-closed config only; no authenticated call made.** Needs project endpoint, deployment and explicit cost approval | `docs/FOUNDRY.md`, issue #14 stays open |
| Azure Container Apps (Bicep + GitHub Actions) | **Prepared, not provisioned.** Template compiles in CI; no resource or public URL exists | `infra/azure/main.bicep`, `docs/AZURE_DEMO_DEPLOYMENT.md` |
| Render free web service | **Hosting target only; not yet applied.** `render.yaml` runs the existing container in public read-only mode; no Microsoft service is involved | `render.yaml`, `docs/JUDGE_ACCESS_DEPLOYMENT.md`, issue #108 |
| GitHub Actions / GitHub CLI | Used: six CI jobs (backend, frontend, browser, container, documentation, deployment-template) | `.github/workflows/ci.yml` |
| Azure databases, Fabric, Azure MCP, Copilot Agent Mode | **Not used** | — |

Do not describe Foundry or hosted agents as working until issue #14's authenticated run exists.

## Reviewer guide

Prerequisites: Windows, Python 3.13, Node 24 (tested baseline). No account, key or paid service.

```powershell
python -m venv .venv
$env:Path = "$(Resolve-Path .venv\Scripts);$env:Path"
.\scripts\start.ps1          # builds and serves http://127.0.0.1:8000
```

1. Open `http://127.0.0.1:8000`. Match "Harbour City comeback" is loaded; choose speed 4× and press Play. Panels stay put while the clock runs.
2. In **Broadcast studio / Verified cues** click the first cue row, then its **Inspect evidence** button. The drawer shows the calculation, **One Moment · Three Stories**, and the source events (click one to jump to it).
3. Change **VIEW** (casual / analyst / broadcaster) and **LANGUAGE** (English / Español / हिन्दी): the facts and cited events do not change.
4. Open **Open event-derived highlight reel** (new tab) for the six-clip reel, or `docs/examples/highlights/comeback-1107.webm`.
5. Control Room (`#/runtime`) needs a local operator token you generate; follow [SUBMISSION_RUNBOOK](SUBMISSION_RUNBOOK.md) steps 1–8 (scenario → step → checkpoint → tactic → paired ForkCast → independent verification). `python scripts/release-smoke.py` runs the same path headlessly.
6. Tests: `cd backend; python -m pytest -q tests` and `cd frontend; npm ci; npm run build; npx playwright test`.

**Public URL: <https://pulse-xi-demo.onrender.com>** (Render free plan, deployed from `main` @ `c16ad54`, 4/4 acceptance tests passed against it on 2026-10-25; [guide](JUDGE_ACCESS_DEPLOYMENT.md), tracker [#108](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/108)). Steps 1-4 work there without installing anything. The first request after 15 idle minutes can take 35-60 s. On the public demo the Control Room, Data Hub imports and Director Studio approval are disabled by design (the app says so); only the local run shows them. The rules allow a test build, but judges are not required to run local builds, so a public URL is needed. Free-plan caveats (15-minute idle sleep, limited CPU) are in the guide.

## Recording storyboard for issue #25 (target 100–108 s, hard limit < 120 s)

Record the build at the frozen SHA on `main` (the Control Room segment must come from a local run; the public demo does not include it), 1920x1080 landscape, fresh browser profile, no
music, no third-party material, no tokens or terminals on screen. Prepare the Control Room
session and checkpoint before recording (the real run takes longer than the video).

| Time | On screen (real actions) | Narration intent |
|---|---|---|
| 0–8 | Match Intelligence, "Harbour City comeback" | Football data tells you what happened, not why. Pulse-Xi explains it with evidence, on synthetic data |
| 8–22 | Press Play at 4×; Event Wire fills, panels do not move; pick a Fan Lens metric | The match is replayed from events; every number below is computed from them |
| 22–42 | Click the first goal cue, **Inspect evidence**; scroll the three stories; click a source event | One moment, three stories, one set of verified events. The broadcast line is only a proposal |
| 42–54 | Switch VIEW to analyst and broadcaster, LANGUAGE to Español | Different audience, same facts |
| 54–62 | Show Control vs Chaos / tactical windows panel | Why the rhythm changed, with the windows shown |
| 62–84 | Control Room: saved scenario, checkpoint, apply tactic, paired ForkCast result, **Verify experiment independently** | Deterministic engine: branch from a checkpoint, compare against baseline, verify by an independent process |
| 84–96 | Highlight reel tab: a goal clip with its evidence line; show the manifest hash | Highlights are built only from event data, no footage |
| 96–106 | Back to README or repository page | Open source. Agent Framework path verified offline; no hosted model claimed |

After upload: confirm logged-out playback, length under two minutes, and record the public URL in
issue #25 and in the form. Never claim a Foundry or hosted-AI run in narration.

## Submission inventory — prepared versus outstanding

| Deliverable | State |
|---|---|
| Public source | [Pulse-Xi](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi), public |
| Pitch, description, technology list | This document (needs a final read-through by the representative) |
| Demo video, public URL | **Not recorded**; owner Diyan, issue #25 (single submission-tracking issue) |
| Working judge access | **Live** at <https://pulse-xi-demo.onrender.com>; verified from outside the dev machine; availability through Nov 10 must be re-checked (#108) |
| Rights and licence | **Decided by the owner, 2026-10-25**: no root licence declared; existing CC0 declaration on the original artwork retained; independent review waived and replaced by a documented checklist run ([memo](LICENSE_AND_RIGHTS_DECISIONS.md)). State this plainly if asked; do not say the assets were independently reviewed |
| Registration and submission | Nothing submitted. The submitting person must be the team's authorized Representative (rules 4.10); tracked with the video in #25 |

## Screenshots (real captures)

[Desktop cue](images/broadcast-evidence/broadcast-cues-1440.png) ·
[desktop proof](images/broadcast-evidence/broadcast-proof-1440.png) ·
[mobile cue](images/broadcast-evidence/broadcast-cues-390.png) ·
[mobile proof](images/broadcast-evidence/broadcast-proof-390.png) ·
[Three Stories](images/three-stories.png)

## Credits

Satvik: frontend, replay, consumers, evidence navigation, Data Hub and observer, final release
integration. Diyan: authoritative engine, persistence, checkpoints and experiments, deployment
template. Mahir: analytics, agents/Foundry adapter, ProofTrail and personalization. Vishwam:
security, licensing and release review. Contributors' existing credits are preserved.
