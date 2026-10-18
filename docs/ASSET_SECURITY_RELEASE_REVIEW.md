# PR #31 asset, security and licensing technical review

Review date: 2026-10-18. Reviewer: Codex operating as Satvik's authorized engineering agent, **not Vishwam**. Initial main `8d6abbb`, asset head `ed53e5a`. No human review or review request was present; #22/#23/#13 had no comments and #24 had only Satvik's previous handoff. No teammate branch/PR was overwritten.

## Executive summary

**TECHNICALLY READY FOR RELEASE REVIEW — HUMAN APPROVAL PENDING.**

Seven native sources and seven GLBs are accounted for. Native reopening/reimport, hashes, material names, bounds and deterministic regeneration were actually tested. Three release-manifest regressions and legacy export nondeterminism were reproduced and fixed. A relevant Windows static-file dependency vulnerability was handled separately in [security PR #36](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/36), preserving the asset approval gate.

This report is technical evidence, not a guarantee of original authorship, legal clearance, public deployment security or formal human approval. `release_approval` remains `pending-team-review`. No checkpoint engine, ForkCast runner, Unreal installation or billable service was introduced.

## Inventory and hashes

Native sources: `assets/blender/{field,ball,player-marker}.blend` and `assets/blender/v2/{field,stadium,ball,player-marker}.blend`. Exports use the same basenames under `frontend/src/features/observer/assets/` and its `v2/` directory. **Seven assets, not seven plus a separately claimed stadium.**

| Asset | Export bytes | Triangles | Current output SHA-256 |
|---|---:|---:|---|
| field v1 | 68,452 | 920 | 9cf7c40308a3e9d98485a7676b6f042b3734fb5fd74456fbd26a9a29d6a24223 |
| ball v1 | 10,556 | 80 | a741caae81b4edce422332e7f9010b6f02e8922bdb57144ef4dead122243c024 |
| marker v1 | 17,108 | 216 | a09dc49fd79688993e3dd6781a9128d37d068b81aaeac98f6b5c644966a77fa5 |
| field v2 | 224,368 | 3,772 | fe8cccc093a6e605290cc661e6e1f29033f84826e83334a0213d1083259d8591 |
| stadium v2 | 714,308 | 13,168 | 0c7891b7da5ebbcf839e1e3974ad71e32011936e8badb284bcefbec361807f31 |
| ball v2 | 30,736 | 1,280 | 260909418e1f655506c158540dbefd9f88cc6c7a64e97dfaf830bfaa1fe01996 |
| marker v2 | 19,672 | 496 | 697b42348e6373973b3e25c012d7f96e6b705aa197e463bc4f739898c6c24cf2 |

Full source paths, source SHA-256, source polygon/byte counts, materials and output budgets are in [manifest](../assets/manifest.json) and the [review inventory snapshot](asset-review-evidence/asset-inventory.json). Active v2 total: 989,084 bytes; archived v1: 96,116 bytes. Native sources and v2 exports were not modified in this review. The three archived v1 binaries were normalized **only in opaque triangle index ordering** to fix reproducibility; bytes/triangle counts/materials/shape remain unchanged. Their previous hashes are retained in the before-fix evidence and Git history. Historical reports describing unchanged v1 bytes apply to their dated revisions, not this correction.

## Provenance assessment

Inspected both committed generators: mesh primitives/direct meshes, original neutral material colors, geometric field markings, seats and stylized symbols; no downloads/imported commercial mesh/texture pipeline. `audit-blender-assets.py` opens every trusted project source with automatic script execution disabled, never saves it, then clears the scene and imports its GLB.

Observed on all seven: no images, linked libraries, sound/movie media, embedded text blocks or object/material/scene drivers; finite mesh coordinates; recorded source polygon/material counts agree; reimported world bounds agree within 0.001 authoring units. See [native audit](asset-review-evidence/native-audit.json). Self-contained GLB checks reject external/data URIs. Khronos checks provide additional geometry/accessor/material validation; intentional open goal nets/flags are not invalid closed-solid requirements.

Two fresh rounds of both generators reproduce every current GLB hash. This supports derivation from these committed scripts. It does **not** prove who authored every idea or owns every right. Human confirmation of authorship, authority to apply CC0 and any undisclosed outside contribution is required.

Actual browser renders show neutral generic stadium geometry, fictional team tint, geometric football and event symbols. No club crests, Premier League marks, player likenesses, stock textures, branded advertising, music, footage or Unreal Marketplace payloads were identified in the inspected sources/exports/rendered views. No independent trademark/legal clearance is claimed. Unreal #13 remains Vishwam's feasibility issue; RTX work #34 belongs to Diyan and is not a release prerequisite.

## Declared licenses and distribution boundaries

| Category | Evidence and required action |
|---|---|
| Original artwork/source GLBs | Existing CC0 declaration in `assets/LICENSE.md`, manifest and export metadata; full CC0 text included. Rights holder must confirm authority; a declaration alone does not establish ownership |
| Offline bpy generators/preview/audit | Existing or explicit GPL-3.0-or-later headers; full GPL text now bundled. Preserve notices and corresponding editable source/scripts when distributing covered work |
| Frontend runtime dependencies | Installed production dependency closure inventory has 23 package instances, declared MIT/ISC/BSD-3-Clause. Actual copyright/license texts bundled at `/assets/THIRD_PARTY_NOTICES.txt` in the build |
| React Three Fiber | Published 9.4.0 tarball omitted license text. Exact tag's upstream MIT text retrieved from the official pmndrs repository and retained locally; no runtime download |
| Khronos Validator | Apache-2.0 development-only package; its actual LICENSE and NOTICES copied to `licenses/`. Not imported into runtime |
| Application and unspecified helper code | **No repository-root software license exists.** Owner must choose/confirm intended distribution/reuse terms, including unmarked helper code. No blanket license was selected or inferred |

Blender distinguishes artwork output from its software licensing: [official guidance](https://www.blender.org/about/license/). GPL source and notice duties are described in the [official GPL text](https://www.gnu.org/licenses/gpl-3.0.html). CC0 applies only to rights the affirmer can waive: [official CC0 terms](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en). These references explain the review questions; they are not a legal opinion that resolves ownership or every licensing combination.

Included license-text sources: GNU official `gpl-3.0.txt`; SPDX's `license-list-data` CC0 text (the direct CC text request returned 403); exact pmndrs tag `v9.4.0/LICENSE`; installed Khronos package. `collect-runtime-notices.py` uses local installed files/cached Fiber text only and can check freshness after `npm ci`. Type/peer packages included in the closure are not a claim that every listed package is actually bundled into JavaScript.

## Threat model and security findings

Scope: trusted original static assets, local replay/seed APIs, asset delivery, package supply chain and the guarded optional provider. No new mutable shared simulation session exists. The deployment still binds loopback by default. Public ingest authentication/rate limits, judge sessions and production cloud policies remain Vishwam's broader #23 scope; the two-origin CORS list is not authorization.

| ID / severity | Evidence and impact | Correction / verification | Remaining boundary |
|---|---|---|---|
| S01 High | Requirements resolved vulnerable Starlette 0.52.1; Windows StaticFiles could resolve UNC before containment, exposing SMB credentials. Relevant `/assets` surface | #36 pins compatible FastAPI 0.143.3 + Starlette 1.3.1; local static guard rejects Windows paths before filesystem I/O. Sentinel-based tests make no external SMB call | Public deployment needs separate operational review |
| S02 Medium | JSON request body was unbounded before Pydantic's 1,000-event limit | #36 adds actual 2,000,000-byte ASGI cap including chunked requests, 413; malformed targets/Host delimiters rejected; invalid JSON remains 422 | Concurrent connections/rate/disk quotas are not implemented by a byte cap |
| S03 Low | pytest 9.0.2 advisory affects shared Unix temp directories | #36 patch-pins 9.0.3; full backend tests | Ephemeral CI helps exposure but was not used to dismiss the advisory |
| A01 Medium | Empty/duplicate manifest or fabricated material names accepted. Three new tests initially failed with DID NOT RAISE | Require complete unique seven-asset inventory and actual GLB material-name match; all three regressions pass | Format intentionally describes this release kit; future assets require a deliberate contract update |
| A02 Medium | Two fresh v1 builds gave different marker hashes; index ordering varied | Canonical opaque indices applied to v1 generator and archived exports; both generations now match all seven committed hashes across two fresh rounds | `.blend` binary byte identity across saves/Blender versions is not promised |
| L01 Low | Declared GPL/CC0 texts and distributable runtime dependency notices incomplete | Bundle existing license texts, Khronos NOTICES and actual MIT/ISC/BSD-3-Clause package notices; reproducible collection/check command | Does not select a root application license or establish authorship |
| L02 Informational / human gate | Root application license and rights-holder confirmation unavailable | Preserve uncertainty and request explicit owner/reviewer decision | Release approval remains pending, never auto-approved |

No dynamic HTML injection/eval was found in the inspected frontend sources. Event strings render through React escaping. Asset URLs are compile-time local Vite URLs, not supplied by users; no remote model/texture URL is accepted by the observer. Match recovery uses a saved match identifier rather than secrets or personal profiles. Import IDs, coordinates, replay cutoffs and page sizes are bounded/validated; request cancellation and asset failure tests cover the relevant UI boundaries. The static kit is bounded below 1.5MB and normal 2D does not initialize it. This bounded assessment is not an exhaustive penetration test.

Focused tracked-file/secret-pattern checks found `.env.example`, not a committed credential file, SQLite DB, dist directory or test artifact. No private-key/token match was found. Optional Foundry dependencies and unrelated globally installed Python packages are not covered by this requirements scan; inference stays disabled unless explicitly authorized.

## Dependency evidence

PyPA pip-audit **2.10.1** was verified against official PyPI project metadata and installed in an isolated ignored tool venv. Before scan: 12 advisory entries in two packages (database duplicates included), saved in [before JSON](asset-review-evidence/python-audit-before.json). After patched requirements: **no known vulnerabilities**, [after JSON](asset-review-evidence/python-audit-after.json). Upstream [Windows advisory](https://github.com/Kludex/starlette/security/advisories/GHSA-wqp7-x3pw-xc5r) confirms the relevant affected/fixed versions. Other Starlette findings concerned URL reconstruction, form parsing and unconstrained HTTPEndpoint dispatch; current app uses explicit JSON routes, but the package upgrade removes the reported affected version regardless.

`npm audit --json` for the current lockfile: zero reported vulnerabilities across production/development scope, [raw report](asset-review-evidence/npm-audit.json). No npm package upgrade was made. Install scripts/dependency roles were inspected: local compiler/bundler setup only, no newly introduced graphics installer. Scans are time-specific database checks, not future guarantees.

## Reproducible verification

Windows, Python 3.13.14, Node 24.12.0, Blender 5.2.2 LTS; Khronos Validator 2.0.0-dev.3.10. Run from root unless marked:

```powershell
python scripts/verify-blender.py
python scripts/asset_contract.py
.\scripts\blender.ps1 --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/audit-blender-assets.py
python scripts/verify-asset-rebuilds.py
python scripts/collect-runtime-notices.py --check
# backend directory
python -m pytest tests -q -p no:cacheprovider
# frontend directory
npm run validate:assets
npm run test:e2e
```

The repeat-build command copies sources/scripts/exports to temporary storage, rebuilds v1 and v2 twice, compares against the committed manifest and cleans up. It never overwrites the production native sources. Manual production export remains supported through `scripts/blender.ps1 --background --factory-startup --python-exit-code 1 --python scripts/build-professional-assets.py`; use a branch because normal export saves source files and updates the manifest.

Evidence: [pre-fix rebuild discrepancy](asset-review-evidence/rebuilds-before-fix.json), [four corrected generator invocations](asset-review-evidence/rebuilds-after-fix.json). Corrected timings: v1 5.16/4.74s, v2 17.65/20.58s, not controlled performance comparisons. Seven Khronos exports pass with zero errors/warnings; unused-UV informational notices are retained. Native probe passes and cleans its temporary files. Eleven asset regressions pass; full asset/security backend suite: **43 passed (3.47s)**. Final production build/strict TypeScript and 29 application/API/browser cases passed in 34.1s, including the new served runtime-notice regression. Final-head CI is linked on PR #31, not inferred from an older run.

## Performance and presentation

No scenery redesign or new GPU cost was added. The active v2 payload remains 989,084 bytes; Low skips stadium. Existing physical Iris Xe run and its explicit rAF-vs-GPU timing limitations are recorded in `SATVIK_INDEPENDENT_HANDOFF.md` and `PROFESSIONAL_3D_GRAPHICS_UPGRADE.md`. This review does not invent RTX or fresh physical FPS numbers. Native bounds/material inspection and actual browser screenshots are separate evidence. Rendering remains event snapshots, not player tracking.

## Reviewer decision and GitHub coordination

Required release reviewer: **@vishwam17-ctrl**, using GitHub's real review-request mechanism after the final head is pushed. No prior approval existed. The request, latest exact head and current CI are verified in the final PR comment. The agent's review is self-review under Satvik's account, not an independent human approval.

Short approval checklist:

- [ ] Confirm the current head and green checks match this evidence; review the before/after findings.
- [ ] Confirm Satvik/rights holder affirms the procedural artwork/source provenance and authority for CC0, including no undisclosed outside material.
- [ ] Review GPL source/notice separation and MIT/ISC/BSD-3-Clause/Apache notices; resolve the root application/helper licensing decision with the owner.
- [ ] Confirm the asset branch's compatibility/fallback/reproducibility evidence and accept release under #23.
- [ ] Post an actual current-head review; only then consider changing release approval metadata through a reviewed change.

Until those human decisions occur, PR #31 stays OPEN; #32/#33 remain intact and draft, with no real checkpoint/ForkCast completion claimed. Safe non-asset security work can merge separately via #36. Diyan still owns state/clock/RNG/queue/interventions/manifests; Mahir still owns branch-scoped evidence integration. #22/#24 support is limited to this technical evidence and corrected instructions; no teammate issue is closed or reassigned.


## Current integration result

Security PR #36 merged normally as main `5f8d9c80ad7b50e7903624d4dfaca807497eee55`; its main workflow is successful: https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39100546734. Clean final main backend run: 32 passed (13.22s). Asset approval is separate and still pending; these main changes do not include the GLB kit.
