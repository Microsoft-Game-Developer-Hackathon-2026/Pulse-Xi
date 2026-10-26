# Licence, rights and release decisions (issue #23)

Prepared 2026-10-25. The sections after "Decisions recorded" are the evidence and options the decisions were based on. No licence file was added, no asset was re-licensed and nothing was approved on behalf of anyone other than the owner's own instruction recorded above.

## Decisions recorded, 2026-10-25 (owner-directed)

The repository owner and declared asset author (satvikp-coder) instructed on 2026-10-25 to finish these items without waiting for teammate reviews. The choices below follow from that instruction. They are recorded accurately, including what they are **not**.

| Item | Decision | What it is not |
|---|---|---|
| Original artwork (CC0) | The existing CC0 1.0 declaration in `assets/LICENSE.md` and `assets/manifest.json` **stays as it is**. No asset, text or metadata was changed, so nothing new was declared. The author is the only committer of all seven assets and `external_assets` is empty | Not a fresh attributable confirmation in the author's own words on GitHub. Anyone relying on CC0 for reuse should know the declaration predates this memo and the manifest still says `pending-team-review` |
| Root licence | **Left undeclared** (option C). The README states that no root licence is declared | Not an agreement of all four contributors: the other three were not consulted. Choosing a licence later needs their consent; until then reuse is not granted |
| Release review | The independent human review was **waived by the owner**. In its place the preparer ran the review checklist (below) | Not an independent review. The `release_approval` field stays `pending-team-review` because `scripts/asset_contract.py` enforces that exact value and it denotes team review that did not happen |

Review checklist as run on 2026-10-25 12:41 UTC against `main` `724dbd2` plus this branch:

| Check | Result |
|---|---|
| Secret-shape pattern scan of all tracked files (AWS, GitHub, OpenAI, Slack, Azure key, JWT, private-key block) | None found |
| Tracked sensitive filenames (`.env*`, `.pem`, `.key`, `.sqlite`, `.db`) | Only `.env.example`, which holds placeholders |
| `render.yaml` credential variables | None (the app refuses to start in public mode if any were set) |
| Asset manifest | 7 assets, `external_assets` empty, all authored by one committer |
| Shipped dependency licences | 42 production packages: 41 permissive, none copyleft; one Python <3.11-only package not read |
| Public boundary | `backend/tests/test_public_deployment.py` (30 tests) and the deployed-URL suite against the live Render service (4 of 4): writes and operator APIs return 403 |
| Dependency audits | `npm audit --omit=dev` 0 vulnerabilities; `pip_audit` on both requirement files none |
| Largest tracked file | `docs/examples/highlights/comeback-1107.webm`, 3.1 MB, generated from event data, no footage or audio |

Not checked: GitHub's own secret scanning (the API returned 404), a screen reader, legal sufficiency of any licence text.

## Facts

| Fact | Source |
|---|---|
| The repository must be public for the entry to be considered; nothing in the rules requires an open-source licence | [Official rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md) section 4.4 (public repository), section 4.6 (ownership) |
| Entrants keep ownership but grant the Promotion Entities a worldwide, perpetual, royalty-free, non-exclusive licence to use the Submission | Rules section 7 |
| The Submission must be solely owned by the Entrant with no other person holding an interest | Rules sections 4.6 and 4.11 |
| There is **no root `LICENSE` file**; a public repository with no licence is "all rights reserved" by default, so others may view and fork on GitHub but have no grant to reuse | `ls` of the repository root, 2026-10-25 |
| Four human contributors by git history: satvikp-coder / Satvik Patel (236 commits), Diyan Patel (57), Mahir Chaudhary (60), vishwam17-ctrl (11) | `git shortlog -sne origin/main` |
| Seven original source assets and their generated GLBs are declared CC0 1.0 in `assets/LICENSE.md` and `assets/manifest.json`, author "Satvik Patel / PULSE XI procedural source"; `external_assets` is empty; only `satvikp-coder` ever committed them; `release_approval` is `pending-team-review` | `assets/manifest.json`, `git log -- assets` |
| Blender generator scripts (`scripts/build-blender-assets.py`, `build-professional-assets.py`) are GPL-3.0-or-later; they are not imported by the web app; the generated artwork is stated to be separate | `assets/LICENSE.md`, `docs/ASSET_SECURITY_RELEASE_REVIEW.md` |
| Shipped third-party packages are permissive: of 42 production packages, 41 are MIT, BSD-3-Clause, ISC, PSF-2.0 or Apache-2.0 and none is copyleft; the 42nd, `exceptiongroup`, applies only to Python below 3.11 and is not installed on 3.13, so its licence was not read here. Dev/build-only tools include 14 MPL-2.0 (axe-core and build tooling) and one CC-BY-4.0 data package (caniuse-lite); none is shipped in the bundle | [third-party-licenses-2026-10-25.json](release-evidence/third-party-licenses-2026-10-25.json) |
| No real match footage, crests, fonts, player likenesses or third-party models are used; data is a newly written seeded generator; the highlight reel draws only from event data | `assets/manifest.json`, `docs/HIGHLIGHTS.md` |

## Decision 1: root licence (options; outcome: left undeclared, see "Decisions recorded")

| Option | Effect | Fit |
|---|---|---|
| **A. MIT** for application code; keep GPL-3.0-or-later headers on the Blender scripts; keep CC0 for artwork | Simple, permissive; consistent with every shipped dependency | **Recommended** if the team wants judges and others to be able to reuse and run it |
| B. Apache-2.0 | Permissive plus an express patent grant and NOTICE handling | Good if patents matter; slightly heavier |
| C. No licence (current state) | All rights reserved; legally clearest about ownership; others cannot reuse | Acceptable for the hackathon; say so in the README |
| D. GPL-3.0-or-later for everything | Copyleft; matches the Blender scripts | Restricts reuse; not recommended |

Before adding any `LICENSE`: (1) each of the four contributors confirms in writing (an issue comment under their own account is enough) that they own their contributions and agree to the chosen licence; (2) the copyright line names the holders they agree on; (3) the README licence section is updated in the same commit. Until then the correct public statement is "no open-source licence has been declared".

## Decision 2: CC0 dedication of the original artwork (outcome: existing declaration retained, see "Decisions recorded")

Proposed text for the author to confirm in a comment on #23, or to change or reject:

> I, Satvik Patel (GitHub `satvikp-coder`), confirm that I am the sole author of the original artwork listed below, that I have the right to dedicate it, that it contains no third-party geometry, textures, fonts, crests, footage or likenesses, and that I dedicate it to the public domain under CC0 1.0 Universal. This covers the artwork and its generated GLB exports, not Blender, the GPL-3.0-or-later generator scripts, or any dependency.

Assets: `assets/blender/{field,ball,player-marker}.blend` and `assets/blender/v2/{field,stadium,ball,player-marker}.blend`, plus the GLBs generated from them in `frontend/src/features/observer/assets/` (hashes and sizes in `assets/manifest.json`). If the author cannot honestly confirm sole authorship (for example, anyone else contributed geometry), do not declare CC0; keep the artwork under "all rights reserved" or the licence chosen in Decision 1 and update the manifest.

## Decision 3: independent release approval (outcome: waived by the owner; checklist run by the preparer, see "Decisions recorded")

Requested reviewer: `vishwam17-ctrl` (original owner of this issue, 11 commits, not an asset author), or `Mahir09-ctrl` if unavailable. The reviewer should confirm, from the linked evidence only, that: no secret is committed (see the bundle credential scan in [PERFORMANCE_AUDIT](PERFORMANCE_AUDIT.md) and the threat model in [SECURITY_THREAT_MODEL](SECURITY_THREAT_MODEL.md); an independent repository-wide scan by the reviewer is still wanted). Scan run 2026-10-25 by the preparer: a pattern scan of every tracked file for AWS/GitHub/OpenAI/Slack/Azure-key/JWT/private-key shapes found nothing; the only history hit for `-----BEGIN` is the regex literal inside the repo's own scanner; the existing triage is `docs/release-evidence/secret-scan-triage.json`. GitHub's secret-scanning alert API returned 404 for this account (not enabled or not permitted), so GitHub-side scanning was not verified; the asset inventory above has no third-party content; the dependency licence file shows no copyleft in the shipped bundle; and public routes are read-only (`tests-deployed/public-demo.spec.ts`, `backend/tests/test_public_deployment.py`). Approval means a comment under the reviewer's own account. It is not approval of legal sufficiency; none of this is legal advice.

## Open items after these three decisions

- Update `assets/manifest.json` `release_approval` from `pending-team-review` only after Decisions 2 and 3 exist.
- Mention the chosen licence (or the absence of one) in the README and the submission description.
- Rules sections 4.6 and 4.11 require the Submission to be solely owned by the Entrant with no other interest, and section 4.10 requires one authorized Representative: the representative should confirm that the four contributors agree to be the Entrant.
