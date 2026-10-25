# Event-derived highlight reels

Issue #18 ("Automated event-derived video highlights with Remotion"). Status: **implemented
without Remotion; see "Why not Remotion" below.**

## What exists

| Piece | Where | What it does |
|---|---|---|
| Manifest | `backend/app/highlights.py`, `GET /api/matches/{id}/highlights?at_second=&limit=` | Deterministic storyboard: every goal plus the highest-priority verified momentum shifts (up to `limit`, default 6, max 12), in match order. Each clip has its title and caption from the verified insight, score before/after, replay window, and the source events (ID, sequence, second, type, team, outcome, normalized start/end). `manifest_sha256` covers the whole manifest. |
| Player | `frontend/src/HighlightReel.tsx`, route `#/highlight-reel?match=<id>` | 1280x720 stage drawn only from the manifest: scoreboard, source-event markers on a normalized pitch, lower third with the evidence line. `&t=<seconds>` pins any frame; `&render=1` hides controls. Opened from Match Intelligence ("Open event-derived highlight reel"). |
| Renderer | `frontend/scripts/render-highlights.mjs` | Records the player with Chromium to WebM, or writes a PNG of one pinned frame. Writes a sidecar JSON listing each clip's event IDs. |
| Example | `docs/examples/highlights/comeback-1107.{webm,json}` | Rendered from fixture `comeback-1107` (seed 1107), manifest sha256 `a9b87246...`: 6 clips, 42 s planned, VP9 1280x720, 3.1 MB. |

## Reproduce

```powershell
.\scripts\start.ps1                      # app on http://127.0.0.1:8000
cd frontend
node scripts/render-highlights.mjs --match comeback-1107 --out ../docs/examples/highlights/comeback-1107.webm
node scripts/render-highlights.mjs --match comeback-1107 --frame 10.5 --out frame.png   # one pinned frame
```

The manifest and its hash are reproducible for a given match and cutoff (tested). The WebM is a
real-time screen recording, so its bytes differ between runs; pinned frames are exact.
Chromium comes from the project's existing Playwright dependency; no new runtime dependency,
paid service, footage, audio, font file or external asset is used (`provenance.external_assets`
is `[]`). There is no audio track and no caption track; the captions are on-screen text.

## Tests

`backend/tests/test_highlights.py` (6): determinism and hash sensitivity, every goal is a clip,
score before/after against an independent goal count, every cited event exists with matching
second/type/sequence and is not later than its clip, replay windows inside the match, cutoff and
limit bounds, endpoint parity and 404/422 handling.
`frontend/tests/highlight-reel.spec.ts` (5): frames pinned at `t` match the manifest (score before
and after the goal, title, caption, evidence count), complete state, 404 shown as an error and not
as fabricated content, axe WCAG scan, link from Match Intelligence.

## Why not Remotion

The issue's checklist asks to "verify license/compatibility". Remotion's
[LICENSE.md](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md) (read 2026-10-25) grants
the free license to an individual, a for-profit organization with up to 3 employees, a non-profit,
or someone evaluating it without commercial use; larger organizations need a paid Company License.
This is a four-person team, and whether that qualifies is a legal question for the team, not
something the code can settle. Adding it as a dependency of a public repository that judges will
run would also pass that question to every user. This implementation therefore needs no Remotion.
If the team confirms eligibility, `HighlightReel.tsx` is a plain React component driven by a pure
time value and can be wrapped in a Remotion composition without changing the manifest contract.

## Limits

- Output is WebM (VP9) with no audio; MP4 would need an encoder not installed here.
- The recording is real time (about 42 s for 42 s of video), not a faster-than-real-time render.
- Clip selection is rule-based (goals first, then verified momentum shifts); it is not a learned
  highlight detector, and the pitch markers are recorded events, not player tracking.
- Imported datasets work through the same endpoint but were not rendered in this verification.
