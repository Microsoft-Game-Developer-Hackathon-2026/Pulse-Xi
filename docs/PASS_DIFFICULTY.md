# Pass difficulty v1

This is a deterministic synthetic pass-difficulty heuristic. It is not a calibrated pass-failure probability, a tracking measurement, or a player ranking. The original fixtures contain short passes, so most scores are low and the high-difficulty filters may be empty.

## Formula and inputs

Version: `synthetic-pass-difficulty/1.0`.

For a pass with start `(sx, sy)` and end `(ex, ey)` in the team's normalized attacking frame:

- `distance = hypot(ex - sx, ey - sy)` in normalized pitch units, never metres.
- `progression = max(0, ex - sx)` in normalized pitch units.
- `raw_score = 100 * ((55/85) * min(distance/100, 1) + (30/85) * min(progression/60, 1))`.
- Round once at the end using `floor(raw_score + 0.5)` and clamp to `[0, 100]`.
- Bands: low `<35`, moderate `35–69`, high `>=70`. These are editorial heuristic labels, not calibrated skill categories.

These are issue #27's proposed distance/progression terms, with their weights renormalized from `0.55/0.30` to sum to one after omitting pressure. Completion outcome does not enter the formula. The same pass geometry produces the same score regardless of replay cutoff, outcome, or later events. Changing formula inputs, weights or rounding requires a new version.

Pressure is **unavailable**, never silently zero. Legacy v1 events do not declare complete pressure coverage or a transform between opposing teams' attacking coordinate frames. A nearby opponent event cannot safely establish pressure on a pass. The current score therefore does not use the proposed ±5-second proximity rule. Passing lanes, defender proximity and forward angle are not scoring factors. A future version may add a pressure factor only after the simulator defines valid common-frame positions and coverage; it must use information available by the pass clock and document timing/spatial boundary tests.

Missing start or end returns `score: null`, band `unavailable`, and an explicit reason. Unknown recipient is valid. Invalid team/player attribution and future/non-pass event requests are rejected. Score packets contain the source pass ID, raw factor values, effective weights, normalized values, unrounded point contributions and formula version.

## API

- `GET /api/matches/{match_id}/passes/{event_id}/difficulty?at_second=N`
- `GET /api/matches/{match_id}/passes/{event_id}/difficulty/evidence?at_second=N`: returns the packet, authoritative source event and independent recomputation verdict.
- `GET /api/matches/{match_id}/pass-difficulty?at_second=N&cursor=0&limit=200`: sequence-based pagination, `next_cursor`, total visible pass count. Maximum page size is 200.
- `GET /api/matches/{match_id}/pass-difficulty/players?at_second=N`: mean, median, sample count and unavailable count per passing actor. No ranking is returned.

Unknown match/pass, non-pass and future pass are 404. Invalid clocks, cursors and limits are 422. Existing match access and ingestion validation apply. No mutation, database migration, credential or paid service is required.

## Evidence and team handoff

`backend/app/pass_difficulty.py::verify_pass_difficulty` reconstructs every packet field from one unique authoritative event, checks replay visibility and compares the entire versioned packet. Altered score, team/player, formula, factor or source IDs fails verification. This is an isolated adapter; it does not redefine Mahir's shared `Insight` categories or modify `evidence.py`.

Mahir can consume the typed DTO and verifier for #16/#20 and agent tools. Future branch integration must receive an already authorized branch-scoped match/event stream; the current API has no sandbox branch semantics. Diyan must supply those contracts before they are added. Vishwam can run the same read-only endpoints in the existing FastAPI container without new environment variables or dependencies.

## Browser experience and verification

Tactical Lab includes an accessible team-scoped pass selector, completed/incomplete high-score filters, selected pass path, factor meter, methodology and source JSON link. Seeking backward immediately hides packets belonging to another cutoff while fetching the new response. Requests abort on seek, match change and unmount. The Favorite Player mode also displays the backend's sample summary.

Run `python -m pytest tests -q -p no:cacheprovider` in `backend`, and `npm run test:e2e` in `frontend`. Focused tests cover geometry boundaries, missing coordinates, outcome independence, reduced weights, malformed coordinates, attributed identities, evidence tampering, future visibility, fixtures, pagination and API validation. Browser tests use the actual FastAPI app for selection, factor output, backward seek, API failure/retry, mobile overflow and player summaries.

Run `python scripts/benchmark-pass-difficulty.py --iterations 30` from the repository root for a bounded local API benchmark. It reports the real environment, serialized bytes and warm in-process latency; it is not a deployment SLA.

Measured on 2026-10-16 with Python 3.13.14, Windows 11 10.0.26300 and Intel64 Family 6 Model 186: 30 warm requests, 148 pass packets, 228,088 response bytes, median 15.175 ms and p95 20.411 ms. The frontend production output was 258.32 kB JavaScript (80.27 kB gzip) and 23.97 kB CSS (6.46 kB gzip). Baseline output was 250.83 kB JavaScript and 19.53 kB CSS. These measurements are from the local development machine and include no network or cloud inference.

Validation for this slice: 22 backend tests and 6 Playwright Chromium tests passed, including the original 8 backend and 3 browser tests. CI initially exposed a concurrent cold-start SQLite migration race. Schema creation now holds the SQLite writer lock and rechecks the version, while journal-mode promotion retries only bounded BUSY/LOCKED failures. Three eight-thread cold-start tests and the browser suite against a fresh temporary database pass. A real browser screenshot of the pass inspector was generated and inspected during the test run. No separate lint or formatting command is configured in package.json; the production build runs strict TypeScript checks.
