# Repository consolidation audit - 2026-10-22

## Scope and main

Starting and currently audited remote main:
`175b7ceb29b2f29437ba6a0a9886934fe5aebc4d`.
[Exact-main CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39671842382)
passed 297 backend / 66 browser plus build, assets and independent verifiers. A fresh
clean-main worktree also passed **297 backend tests (155.01 seconds)** and the full
**66 browser tests (5.9 minutes)** during this audit, including the unchanged
maximum-history case (3.9 minutes). Strict TypeScript and production build passed.
Updated PR CI belongs in the PR's execution evidence; do not interpret a historical
green run as validation of a different SHA.

No PR had all required review/dependency gates satisfied. No direct main push,
force-push, draft merge or substituted approval was performed. The existing local
main fast-forwarded from 4d1d11c to the exact remote main without discarding changes.

## Open PR disposition

All 13 initial PRs contain necessary unique work or active design work; none was
closed merely to reduce the count. Ready means technically reviewable, not approved.

| PR | Disposition | Outstanding decision/dependency |
|---|---|---|
| #74 | Ready; archive-reuse correction | Diyan/Mahir review; prioritize its reproduced large-export resource issue |
| #73 | Documentation and this consolidation record | Diyan documentation review |
| #71 | Ready; scoped Premium Glass | Diyan/Mahir review; no backend diff |
| #75 | Ready; direct cue proof and competition package | Diyan/Mahir review |
| #57 | Ready; native-period increment | Diyan/Mahir review; retain native clocks and schema 4 metadata |
| #42 | Ready; recorded Control vs Chaos | Mahir feature review; preserve original formulas |
| #48 | Reconciled with main | Preserve both preference initialization and viewport hook; new locale/scenario regression |
| #51 | Reconciled with main | Preserve main's StoredCheckpoint/schema 4 contract and ProofTrail route; requires owner review and #54 isolation acceptance |
| #54 | Stacked on #51; request isolation still necessary | Mahir review; no equivalent cancellation fix on #51 was assumed |
| #58 | Draft; Diyan approved its previous exact head | Recorded #42 and native #57 dependencies remain unmerged; Mahir analytical review |
| #55 | Draft; bounded evidence tools | Mahir orchestration acceptance; private runtime comparison authorization remains undefined |
| #56 | Draft; cost-gated validation | Mahir/security review and separately authorized provider execution; no billable call made |
| #50 | Draft; design contract only | Mahir interface/design review; no mutable Broadcast Studio claimed |

### Actual conflict resolutions

- #48 `frontend/src/App.tsx`: retain `useStableViewport()` and
  `useState(readFanPreferences)`. Existing main runtime/scenario changes are retained
  by the normal merge. Regression covers Spanish preferences through authenticated
  scenario saving and back, without token persistence. Its test operator is isolated
  from concurrent runtime tests.
- #51 `backend/app/sandbox/api.py`: retain ProofTrail's import/route and current
  main's checkpoint metadata/reproduction imports; remove obsolete `CheckpointView`
  import. Added real API coverage for unchanged original UTC/hash, no-store and
  wrong-owner 404 concealment. Full backend: 301 passed; eight affected browser tests
  and TypeScript/build passed on the reconciled branch.

These normal merges preserve contributor history and do not grant feature approval.

## Safe remote branch removals

Remote branches decreased from 52 to 42. Every deletion rechecked current SHA,
protected status, open PR head/base references and worktree usage immediately
before a normal remote deletion; absence was verified afterward. No teammate-owned
branch was deleted. No local worktree was removed or reset.

| Deleted Satvik branch | Last SHA | Preserved implementation/history |
|---|---|---|
| historical deleted branch docs/independent-integration-handoff | `2711c31b0ae8833932f24c68c74d8811e88713eb` | `origin/main` |
| `feat/10-sandbox-control-room` | `5eea5cfed8a97840bd96963954f8a4b56bf9e57f` | `origin/main` |
| `feat/11-three-d-observer` | `bade6a2b384eda91d7fd8ddaf95294b011a43fbc` | `origin/main` |
| `feat/27-pass-difficulty` | `fdd0de14b85ee19f654b4bc2cffd2e6f1fc5a269` | `origin/main` |
| `fix/local-static-security` | `51f05d85ac4ce8fe377302a95da49417c6196277` | `origin/main` |
| `prep/6-checkpoint-contracts` | `dfa420af237c59ec694a989449c77e645ade6ecb` | `origin/prep/8-forkcast-comparison` |
| `validation/asset-runtime-final-acceptance` | `52e9a847a087e899df320d2acd7dcc40a704f336` | `origin/docs/integrated-platform-readme` |
| `validation/native-team-compatibility` | `ba628ff2ef6862ac9aa1d2014d5cfba4d83f8763` | `origin/docs/integrated-platform-readme` |
| `validation/runtime-control-team-compatibility` | `a720627bfd569e6ecc8c6fc93c557174533cb642` | `origin/docs/integrated-platform-readme` |
| `validation/satvik-full-scope-acceptance` | `52a8f0bd14e4eba143d5e10224a09e7f557cd9fe` | `origin/docs/integrated-platform-readme` |

Unmerged artwork/preparation tips and all active PR heads/bases remain. Teammate
merged branches remain until their owners authorize removal. Checked-out historical
branches remain even when redundant: preserving an active worktree takes precedence
over reducing the branch count. Old validation commits remain reachable from the
retained integrated-platform documentation branch; CI artifacts and PR discussion
were not deleted.

## Issue cleanup

[Issue #44](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/44)
was verified completed by merged PR #45, merge 4d8a01e5, retained in current main.
Sixteen fresh trace/command/release-security tests passed. The issue's outdated
pending-integration status was marked historical and it was closed as completed
with [evidence](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/44#issuecomment-6333525501).
All Satvik-assigned issues were already closed. Issues #23 (licensing/release) and
#25 (actual video/submission) remain open; broader teammate acceptance issues were
not closed on the strength of unrelated tests.

## Shipped versus candidate

Main includes runtime, saved scenarios, schema 4 checkpoints, ForkCast, independent
reproduction, Pass Difficulty, sparse-event 3D, timed cues and limited template
recaps. It does not include native-period analysis #57, recorded/runtime Control vs
Chaos #42/#58, FanDNA expansion #48, branch ProofTrail #51/#54, Glass #71, archive reuse #74,
direct cue proof #75 or draft agent tools #55/Foundry validation #56. Existing recorded
insight proof is distinct from the pending branch-comparison ProofTrail feature.

The non-release `validation/competition-experience` candidate combines #71/#74/#75
at 50c01a135e96f647733f9b66522445192e9a0fa7. Its 79 local browser tests pass, but
it is not main, a substitute for review, or permission to distribute assets.
No hosted inference, cloud provisioning, public deployment or submission occurred.

## Resume and review

Next merge decision: Diyan/Mahir review #74 at its actual head, then normal eligible
merge and exact-main verification; recalculate remaining PRs after any main move.
Vishwam and rights holders retain issue #23's distribution/release decision. Keep
judge access, final video/public URL and representative submission as explicit gates.
