# Submission runbook — prepared, not submitted

The official [rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md)
were checked on 2026-10-21 UTC. Submission closes **October 27, 2026 at
11:59 PM Pacific Time** (October 28, 06:59 UTC / 12:29 India).
The video must be **shorter than two minutes**, show the real running product,
and have a public video link. Supply a public source repository, English materials
or translations, authorized content, and accessible working-project testing
instructions. The rules allow a website, functioning demo **or test build**;
they do not justify bypassing #21's separate public-demo security gate.

## Candidate identity and evidence

- Source: [Pulse-Xi](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi).
- Audited starting main: `c5a93f46a24fa857318f237f37f9184a4b4d90dc`;
  [baseline CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39664390354).
- Final candidate: select the **merged release-verification PR commit and its exact
  successful main Actions run**, recorded in the PR/issue evidence. Freeze that SHA
  before capture; never use a green check from an earlier revision as its evidence.
- [Release evidence / risks / measurements](RELEASE_READINESS.md),
  [machine-readable snapshots](release-evidence/),
  [architecture diagrams and deterministic contracts](AUTHORITATIVE_ENGINE.md),
  [operator guide](LIVE_SANDBOX.md).
- Runtime: synthetic fictional events and qualitative model comparisons. These
  are not Premier League events, measured athlete motion, calibrated probabilities
  or verified real-world tactical predictions.
- Microsoft stack: repository uses an optional Microsoft Foundry / Agent Framework
  provider path. Local narratives use deterministic templates and evidence checks.
  **Authenticated inference has not been demonstrated by this release audit**;
  #14/#15 and open PRs #55/#56 remain separate. GitHub Actions is genuinely exercised.
- Public deployed URL: **not established**. #21 still requires cost authorization,
  configuration, durable storage and public-access verification.
- Recorded final video / public video URL / submission confirmation: **not created**.
- Rights clearance: **pending** #23 (technical asset pipeline #12 is closed); root application/helper licensing unresolved.
  Asset declarations and third-party notices are technical inventory, not approval.

## Rehearse the real judge journey

1. Follow [README startup](../README.md#windows-quick-start). Use Python 3.13 / Node
   24 for the tested baseline, fresh dependencies, and separate disposable DB paths
   for rehearsal. Leave Foundry disabled. Use only locally provisioned operator
   credentials; never record or export them. The helper does not load `.env`.
2. Run `python scripts/release-smoke.py` after the frontend build. It checks the
   complete backend path through actual local HTTP and two separate CLI verifier
   processes, without touching personal databases or calling a hosted service.
3. Open `http://127.0.0.1:8000/#/runtime`. Connect before recording. Select Balanced,
   seed 7, duration **5400** for compatibility with the recorded-analysis adapter.
   Save the scenario; show saved scenario ID/hash, seed and provenance; use the
   saved selector to reload it. Keep the advanced resolved JSON inspectable.
4. Create a session. Set **Step seconds** to 60 and select **Step engine**. This
   advances authoritative backend ticks, not a browser clock. Show generated events.
   The scene is a recorded-event observer, not continuous physical tracking.
5. While paused, save a checkpoint and inspect its original UTC/tick/state hash.
   Legacy timestamps must read unavailable, never a made-up calendar time.
6. Under Tactical intervention, choose home pressing 90, **Apply future tactic**,
   then step one tick. Show requested/effective tick and pending→applied history.
   Reset creates a fresh session; restore creates a branch. Do not narrate in-place
   undo, substitutions or rewind of immutable history.
7. Select the earlier paused checkpoint with remaining time. Choose a tempo
   variation, **Paired trials = 1**, **Experiment horizon seconds = 60**, then
   **Run paired ForkCast**. Show actual baseline/variation metrics, branch sources
   and event evidence; sparse/zero differences are honest outcomes.
8. Select **Verify experiment independently**; wait for the actual response.
   Download the experiment manifest and verify from `backend`:

   ```powershell
   python -m app.sandbox.verify_experiment <downloaded-json-file>
   ```

   Runtime manifest counterpart: `python -m app.sandbox.verify_manifest <file>`.
   Unsigned hashes verify reproducibility, not authorship/timestamp authenticity.
   If an experiment exceeds the 2 MB online upload limit, show the offline verifier
   (20 MB bound), never turn unavailable verification into a PASS.
9. Expand **Recorded-event analysis, bookmarks and 3D** for real event-derived pass
   analysis/evidence on the 5400-second configuration. Use 2D/procedural fallback
   unless asset approval is recorded. Native-period analysis #57 is not implied.
10. Refresh and confirm stored session/experiment recovery. Run the full release
    matrix and both committed example verifiers at the frozen SHA before upload.

## Draft recording script — target 110 seconds

This is a capture plan, **not evidence that a video exists**. Rehearse timings on
the actual machine. Never speed up a failed action or edit an unavailable feature
into an apparent success. Cuts may omit waiting but must not misrepresent results.

| Time | Actual screen / action | Suggested English narration |
|---|---|---|
| 0–12 s | Saved scenario, preset/seed/hash; fictional-data notice | “Pulse-Xi turns synthetic football events into inspectable match intelligence. This saved scenario has a reproducible seed and configuration hash.” |
| 12–25 s | Step server, event list and 2D observer | “The backend owns match time and outcomes. These are generated events, not real football footage or tracked player motion.” |
| 25–39 s | Save/inspect paused checkpoint, original UTC and tick | “This checkpoint preserves exact state and random-stream counters. Calendar metadata stays outside deterministic hashes.” |
| 39–53 s | Apply pressing change; step; audit shows effective tick | “A validated tactical change takes effect at the next legal tick, with an audit trail.” |
| 53–76 s | Paired ForkCast from earlier checkpoint; metrics/source events | “Isolated branches share a starting state. This comparison comes from their actual events, not a promised scoreline or calibrated forecast.” |
| 76–94 s | Real verification response, downloaded file and successful CLI | “The exported manifest replays independently. Changing supported inputs or output hashes causes verification to fail.” |
| 94–104 s | Event-derived analysis and source evidence | “Facts and supporting events remain inspectable alongside the synthetic replay.” |
| 104–110 s | Honest status card / source URL | “The local workflow is verified. Hosted Microsoft AI and public deployment remain separately gated; fallback is clearly labelled.” |

Optional live Microsoft AI footage can replace the last section **only after** an
approved actual call, redacted evidence, current failure-path tests and truthful
provider status exist. Do not record mocked provider tests as inference. A limited
local-only video is not a claim that all hackathon technology goals are satisfied.

## Capture, upload and final checks

- Record the actual app with a locally available recorder; check permission before
  using any external music/media. Use English narration/captions, clear font sizes,
  1080p if practical, and keep actual duration **below 120 seconds** (target 110).
- Use a clean browser profile; close personal tabs, notifications and terminals
  containing paths or secrets. Connect the operator before capture. Recheck every
  frame, download and terminal output for credentials and personal information.
- Store approved final video, SHA-256, duration, script version, source SHA, CI URL,
  redacted screenshots and reproduction files together in a **private local evidence
  directory**. Do not commit raw recordings, real tokens, local DBs or unreviewed media.
  Committed technical JSON reports belong in `docs/release-evidence/`.
- Rights holders record actual asset/root/helper license decisions in #23;
  preserve third-party notices. No agent may sign these decisions for them.
- Authorized team representative checks eligibility/registration and required
  project-page fields. Review the current rules again immediately before upload.
- If using a deployed demo, obtain explicit cost authorization first, follow #21,
  test HTTPS/REST/WS/restart and an unauthenticated judge browser at the exact SHA;
  use judge-scoped credentials, never developer administrator credentials.
- Alternatively prepare a reproducible test build with safe testing instructions
  as permitted by the rules; do not label it an Azure deployment or public URL.
- Upload the real video to a permitted public platform, test playback logged out,
  verify public repository and all links, then submit before the deadline.
- Archive the real confirmation/time and public URLs. Keep judge access available
  through the published judging period. Only then assess #25 for closure.

Current stop signs: #23 rights/license decisions; #14/#15 approved Microsoft AI
validation if claimed; #21 public deployment if selected; actual capture/edit,
public video playback, representative submission and confirmation. No fabricated
approval, provider output, video link or deployment substitutes for these gates.

## Competition evidence and story

See the [judging evidence matrix](HACKATHON_JUDGING_EVIDENCE.md) and
[submission working package](HACKATHON_SUBMISSION_PACKAGE.md) for the event-to-story
capture sequence, category evidence and mandatory registration/access/video gates.
These documents do not certify submission or an authenticated hosted model run.
