# Hackathon judging evidence — facts before claims

Rules checked October 22, 2026 against the [official rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md).
This is an evidence map, not an official score or eligibility certification.
Starting main: `175b7ceb29b2f29437ba6a0a9886934fe5aebc4d`;
[exact-main CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39671842382).
The broadcast evidence action and its new browser tests belong to this PR until merged.

| Criterion (20% each) | Working evidence and code | Executable check | Demo moment | Owner / remaining gap |
|---|---|---|---|---|
| Technological Implementation | Server-owned engine, immutable checkpoints, paired ForkCast and independent replay in `backend/app/sandbox/`; persisted scenario library | `test_authoritative_engine.py`, `test_checkpoint_metadata.py`, `test_reproduction.py`, `test_scenario_library.py`; `scripts/release-smoke.py` | Pause, restore an isolated branch, verify an actual experiment bundle | Diyan engine; Satvik consumers. Freeze and rerun the final merged SHA |
| Agentic Design & Innovation | Optional Microsoft Agent Framework analyst/editor handoffs in `backend/app/agents.py`; deterministic packet audit rejects unsupported references/numbers | Provider and audit cases in `test_simulation.py`; draft #55/#56 have additional bounded tool workflows | Show actual stage/tool traces only from an authorized executed run | Mahir. Draft tools remain unmerged; hosted inference is unverified. Templates are not model agents |
| Real-World Impact & Applicability | One synthetic event feeds inspectable metrics, source evidence, audience-specific recaps and timed JSON cues in `backend/app/evidence.py` | `test_simulation.py`, `test_pass_difficulty.py`, `broadcast-proof.spec.ts` in this PR | Same clock: Fan → Analyst → Broadcaster; inspect the same event IDs | Satvik integration, Mahir analytical features. No measured customer adoption or calibrated real-football forecast |
| User Experience & Presentation | Replay, evidence drawer, accessible 2D/3D fallback, scenario library and recovery | `replay.spec.ts`, `sandbox.spec.ts`, runtime and observer browser suites; new desktop/mobile cue evidence journey | Keyboard-open proof from the cue, inspect sources, Escape returns focus | Satvik. Premium Glass #71 is review pending; final video not yet recorded |
| Adherence to Hackathon Category | Synthetic football intelligence with contextual explanations, personalization and exportable narrative cues; optional Microsoft workflow | Public source, real fixture/API/browser execution, independent manifests | Explain event → evidence → story → cue, then scoped tactical what-if | Team. Category selection must match executed Microsoft evidence; SDK installation alone is insufficient |

## Category decision

**Best Multi-Agent System is a conditional target**, requiring the distinct roles,
structured handoffs, bounded tools, recovery and actual execution evidence from
Mahir's reviewed workflow. Current deterministic templates must not be presented
as those agents. Best Use of Microsoft Foundry needs meaningful authorized provider
evidence; none was generated here. Azure Cloud Native is unsupported by local
execution alone. Enterprise applicability is a use case, not deployment readiness.
Select the category after validating the final integrated workflow.

## Mandatory submission gates

- Authorized representative confirms registration by October 20 at noon Pacific,
  team eligibility (maximum four), and project creation after September 29. The
  registration window has passed; repository activity cannot prove registration.
- Submit before **October 27, 11:59 PM Pacific / October 28, 06:59 UTC / 12:29 IST**.
- Public repository is available. A working website, demo or test build still
  needs clean-environment judge-access verification through November 10 judging.
- Record the actual application in English (or provide translation), under two
  minutes, and publish on an allowed platform. No recording/upload is asserted.
- Resolve #23 artwork authority, root/helper licenses and release approval with
  Vishwam and the rights holders. Technical #12 completion does not grant rights.
- Keep provider costs, deployment, upload and final submission under their actual
  human authorization gates. No hosted call or cloud resource was created here.

See [submission package](HACKATHON_SUBMISSION_PACKAGE.md),
[runbook](SUBMISSION_RUNBOOK.md) and [release risks](RELEASE_READINESS.md).

## Offline Microsoft compatibility observed in this session

These are separate draft heads, not features merged into this PR or main:

- #56 `940ff0599bf84e9556211828aae52288608e2e20`:
  `python backend/scripts/foundry_smoke.py --check-only` returned
  `sdk_compatibility_ok`, `network_call: false`, `authenticated: false`.
  Nine focused smoke/auth tests passed. This verifies imports/construction and
  local safety cases, not provider behavior or Microsoft category eligibility.
- #55 `1ec2effbf6eddd6ef03a297a1b4db90a802cfc19`:
  five `test_agent_tools.py` cases passed. Tool comparisons remain explicitly
  unavailable until a reviewed private-source authorization contract exists.

No draft was merged, hosted request made, token uploaded or paid service enabled.
