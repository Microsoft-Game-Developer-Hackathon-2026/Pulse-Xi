# Creative media decision and provenance workflow

## Release decision (2026-10-21)

**Decision: no Higgsfield-generated or other new creative media is included in this release.**

The current interface already has an original CSS/SVG visual language, so a title intro, synthetic stadium shot, transition, promotional clip, or cover image is optional polish rather than a requirement for demonstrating the working application. No Higgsfield generation credits or other paid media services have been authorized for this work. The prerequisite security, legal, licensing, and provenance audit in [issue #23](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/23) is still open. There is therefore no approved asset to integrate.

This is a deliberate no-use decision, not a claim that Higgsfield output has been reviewed or is cleared. Existing application visuals and any other assets remain subject to the repository's wider release audit. Reconsider new media only after a specific creative brief, rights review, and explicit cost approval are recorded. Keep the application demo and its evidence focused on actual product behavior.

## Proposed creative brief (for a future approved request)

- **Purpose:** Optional presentation polish for a clearly identified intro, transition, promotional piece, or cover.
- **Audience and placement:** Hackathon judges and reviewers; outside the product evidence pipeline.
- **Content boundary:** Original, fictional football presentation imagery only. No real match footage, club or league marks, player likenesses, copied artwork, or visual claims that imply recorded gameplay.
- **Product boundary:** Static presentation files only. Never insert generated media into match events, replay evidence, analytics, or claims about simulation output. The core demo must remain usable without the media.
- **Accessibility and performance:** Provide a text equivalent for meaningful visuals, respect reduced-motion preferences, and set a file-size/loading budget before production.
- **Approval gate:** Name the exact tool/model and plan, intended prompt and output, expected credit or monetary cost, applicable usage-rights terms, and approver. Do not generate or spend credits until that request is explicitly approved.

## Provenance record

There are **zero new creative assets shipped by this decision**; the asset list for this workflow is empty. This document records the decision and does not replace the repository-wide asset inventory or audit.

For each future asset, add one record before integration with all fields below. Use `not applicable` only when the field truly does not apply; use `pending` while review is incomplete. A pending record is not permission to ship.

| Field | Required record |
| --- | --- |
| Asset ID and file path | Stable identifier and repository-relative path |
| Purpose and usage location | Presentation placement, plus confirmation it is outside product evidence |
| Creator/owner | Human or organization responsible for the output |
| Source/tool and model/version | Exact generator or authoring software; include plan/tier where relevant |
| Prompt and source inputs | Exact prompt; list input files and their origins, or state none |
| Creation date | ISO 8601 date |
| Rights and license | Applicable terms/version or license, attribution obligations, and reviewer/evidence reference |
| Cost | Credits and monetary cost, including currency; zero only when verified |
| Approval | Approver, date, and explicit cost/rights approval evidence |
| Integrity | SHA-256 checksum of the final file |
| Review status | Rights, trademark, accessibility, performance, and security review outcomes |
| Removal/fallback | Original CSS/SVG or another cleared fallback and removal owner |

## Review and integration checklist

1. Propose a specific brief and identify the target placement and fallback.
2. Verify applicable usage rights, input provenance, trademark/likeness exposure, accessibility needs, and output constraints.
3. Estimate credits and money. Obtain explicit approval before any generation or paid action.
4. Generate or author only the approved scope. Record provenance and calculate the final file checksum.
5. Review the actual output and update the manifest. Reject unsupported legal/ownership claims and any asset that resembles real match evidence.
6. Integrate only static presentation media; show a clear “presentation art” label where a viewer could mistake it for match capture.
7. Confirm the fallback works, the media budget is met, and the product evidence path contains no generated media.
8. Link review evidence in the pull request and release audit. Remove the asset if approval, provenance, or rights cannot be demonstrated.

## Scope

This document does not authorize spending, create or endorse a Higgsfield account or plan, establish legal clearance, or approve any asset. It records the current no-use decision and a workflow for a separately approved future request.