# Demo video: storyboard, timings and narration

Final file: `artifacts/demo/pulse-xi-final-demo.mp4` (110.60 s, 1920x1080, 30 fps). Not committed to Git
(see [production report](VIDEO_PRODUCTION_REPORT.md)). Captions: `artifacts/demo/pulse-xi-final-demo.srt`
(20 cues, burned into the video as well). Full spoken text: `artifacts/demo/pulse-xi-narration.md`.

Every scene is one **continuous, real-time recording of the real application**; nothing was sped up,
reordered, mocked or edited into a fake state. Cuts only remove page-load time before each scene
(and, in the Control Room scene, the typing of the throw-away local operator token). Pointer and
highlight rings are overlays drawn on top of real mouse events; the small chip at the top names the
source of each scene.

| Video time | Scene | Source (chip) | Real actions on screen | Narration |
|---|---|---|---|---|
| 0:00-0:21 | Title, then replay | Live public demo | Original title card (0-4 s). Seek slider dragged to 14:00, speed 2x, play. Goal at 16:40 moves the score 0-0 to 0-1; metrics and event wire update; the layout stays put | n0, n1 |
| 0:21-0:43 | Evidence and One Moment, Three Stories | Live public demo | First cue (16:40 goal) clicked, Inspect evidence, drawer shows the calculation and two source events, then the analyst, fan and director lenses, the PROPOSED cue label and the computed "every lens cites only this moment's 2 verified source events" check | n2 |
| 0:43-0:55.6 | Audience and language | Live public demo | At 78:20: VIEW analyst, then broadcaster, then language Espanol. Wording changes, goals and source counts do not. The 1-2 s "loading recap" moments are real latency of the free host | n3a, n3b |
| 0:55.6-1:06.6 | Control vs Chaos, pass inspector | Live public demo | At 70:00: rhythm bars (Northbank United activity index 1 to 7), turning point opened; pass inspector for the 69:39 pass (heuristic 16/100, pressure context shown as unavailable) | n4 |
| 1:06.6-1:25.6 | Control Room | **Local run** (operator tools are disabled on the public demo) | Connect operator, create scenario (seed 98765, 300 s), step 20 s, save exact checkpoint, apply future tactic (home pressing 100 at 00:21), run 1 paired ForkCast trial (60 s horizon), comparison table, Verify experiment independently. 19 s of a continuous 22 s take, real time | n5a, n5b |
| 1:25.6-1:37.6 | Event-derived highlight reel | Live public demo | `#/highlight-reel` plays in real time: clips 2 and 3 (56:40 and 65:00 goals) with score, source events and verified label; no footage | n6 |
| 1:37.6-1:50.6 | Close and end card | Live public demo | Application at full time (3-2). End card from 1:44.8: live demo URL, repository URL, "Rule-based explanations, Microsoft Agent Framework path verified offline, no hosted model claimed". Fades out | n7 |

Legibility aids (all disclosed): browser zoom 1.25 on the evidence scene, 1.3 on Control vs Chaos, 1.2 on the Control Room and 1.5 on the reel (its stage is 1280x720); the replay and audience scenes are unzoomed. No element was added to the product UI.

## Features deliberately not shown

Hosted Foundry or agent runs (none exist), the Director Studio approval step (needs a producer token),
the 3D observer, imports and saved scenarios. They are either blocked or not needed for the story.

## Timing against the official limit

Rules section 4.4: the video must be **under two minutes**. Final length 110.60 s, a 9.4 s margin.
Re-encoding or platform processing does not change the duration.
