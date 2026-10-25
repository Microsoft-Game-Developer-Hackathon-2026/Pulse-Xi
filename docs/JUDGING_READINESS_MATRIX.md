# Judging readiness matrix (2026-10-24)

Source: official rules §6.2 (Judging Criteria, equally weighted, 20% each) and §4.4/§4.8
(submission and testing), read from the organizer repository on 2026-10-24. Scores are
not predicted; this is an engineering assessment of evidence only.

Constraints from the rules that shape the demo: the video must be **under two minutes**
(judges need not watch longer), show the project working on its target platform, and have a
public URL; judges must be given free access to a working project (link, demo or test build)
through the judging period (Oct 27 – Nov 10, 2026); the pitch must name the Microsoft/Azure
technologies actually used.

| Criterion (official wording, abridged) | What PULSE XI shows | Proving journey | Evidence | Gaps / limits |
|---|---|---|---|---|
| **Technological Implementation**: creative, optimized synthetic data; quality software practices; use of hero technologies; structured, documented, maintainable code | Deterministic seeded engine, replay/checkpoint/restore, paired ForkCast with independent verifiers, SQLite schema 4, strict CI | Control Room: scenario → step → checkpoint → restore → ForkCast → verify bundle | backend 549 passed; browser 142 passed (final-pass branch; 547/141 at `92d05ed`); `scripts/release-smoke.py` passed (real HTTP, disposable DBs, 2 verifiers); API p50 6.6–34.6 ms, p95 8.7–47.5 ms (40 warm samples, [benchmark](benchmarks/public-api-2026-10-24.json)) | Hero technologies (Foundry, Agent Framework, Azure services) are **not executed live**: no credential/cost authorization. Do not claim them |
| **Agentic Design & Innovation**: agentic patterns, orchestration/MCP/multi-agent, novelty | Role-scoped tools, deterministic Evidence Auditor, offline specialist workflow; One Moment · Three Stories frames one verified moment three ways | ProofTrail drawer on a goal cue | `test_agent_tools.py`, `three-stories.spec.ts` (3 tests) | Three Stories and the auditor are **rule-based**, not model-backed. Hosted multi-agent evidence is blocked (audit C6/A3). Weakest criterion |
| **Real-World Impact & Applicability**: problem significance, deployability, impact | Explains why a moment matters with inspectable source events; audience-specific language with identical facts; reproducible tactical experiments | Seek to goal → evidence → switch persona/locale | `broadcast-proof.spec.ts`, `test_fandna_locales.py` | Synthetic data only; no real tracking/speed data; not deployed publicly; local-first security model |
| **User Experience & Presentation**: intuitive design, clear demo video, frontend/backend balance | Precision Glass UI, stable replay (page CLS < 0.001, scroll drift 0), route-health sweep at 1440/390 px, keyboard/reduced-motion coverage | Replay at 4× while scrolled on analysis panels | `replay-stability-metrics.spec.ts`, `route-health.spec.ts`, `glass-accessibility.spec.ts` | Final video does not exist; Event Wire rows still move inside their panel (animated, reduced-motion aware); INP/LCP unmeasured |
| **Adherence to Hackathon Category**: complies with the category description | Five-stage ingest → interpret → explain → render → personalize works on deterministic data | Hero journey in the readiness report §I | Audit rows C1–C5 verified | The category's AI-powered requirement is only satisfied by rule-based evidence until a hosted run is authorized (C6 blocked) |

## Submission gates (rules §4.4, §4.8)

| Gate | State |
|---|---|
| Public repository | Verified public |
| Pitch naming Microsoft/Azure tech actually used | Package exists; must not claim hosted Foundry/Agent Framework runs |
| Video < 2 min, public URL | Not recorded |
| Judge access through Nov 10, free | **Not provisioned.** Render Blueprint and acceptance suite ready; owner #108 |
| Rights/originality sign-off | Pending human decisions; memo prepared ([LICENSE_AND_RIGHTS_DECISIONS](LICENSE_AND_RIGHTS_DECISIONS.md)), #23 |
| Submit by Oct 27 11:59 PM Pacific (Oct 28 12:29 PM IST) | Not submitted; Representative unconfirmed (#109) |
