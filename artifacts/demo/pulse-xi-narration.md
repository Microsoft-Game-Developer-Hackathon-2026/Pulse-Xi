# PULSE XI demo video: narration script

Spoken text exactly as synthesized (Windows SAPI voice `Microsoft Zira Desktop`, offline). Times are positions in `pulse-xi-final-demo.mp4`; total video 1:50.60 (110.6 s), 194 spoken words.
The product name is written PULSE XI on screen and spoken as "Pulse X I" (letters), because the team has not defined a pronunciation.

| Time | Segment | Spoken text |
|---|---|---|
| 0:00.60-0:09.55 | n0 (replay) | Football is more than the scoreline. Pulse X I turns synthetic match events into intelligence you can inspect, compare and replay. |
| 0:10.40-0:19.64 | n1 (replay) | Here a synthetic match replays from recorded events. Every statistic is computed from them, and the screen stays steady while it plays. |
| 0:21.80-0:40.69 | n2 (evidence) | Pick a goal and ask why it matters. The evidence drawer shows the calculation and its source events. One moment, three stories: analyst, fan and broadcast director, all citing the same events. The director's cue stays a proposal until a producer approves it. |
| 0:43.80-0:48.12 | n3a (audience) | Change the audience or the language, and the wording changes. |
| 0:53.30-0:55.26 | n3b (audience) | The facts do not. |
| 0:56.40-1:04.29 | n4 (intelligence) | Control versus Chaos shows how the rhythm of play shifted, and the pass inspector rates each pass with an explainable heuristic. |
| 1:07.40-1:18.50 | n5a (control) | In the Control Room, a deterministic engine runs the match on the server. Save a checkpoint, change a tactic, and run a paired comparison against the baseline. |
| 1:22.00-1:24.82 | n5b (control) | Then verify the result independently. |
| 1:26.40-1:34.24 | n6 (reel) | Highlights are built only from event data. Each clip shows its score and its source events, with no match footage. |
| 1:38.40-1:47.68 | n7 (close) | Everything is synthetic and rule based, and the Microsoft Agent Framework path is verified offline. The code is public on GitHub. |

Claims in the narration and their basis: replay and statistics are computed from recorded synthetic events (`backend/app/analytics.py`); the evidence drawer, three lenses and the PROPOSED cue label are `frontend/src/ThreeStories.tsx`; wording changes with audience and language but not facts (`backend/tests` recap tests, `frontend/tests/broadcast-proof.spec.ts`); Control Room, checkpoint, tactic, paired ForkCast and independent verification are the real flow in `frontend/tests/runtime.spec.ts`; highlights are `docs/HIGHLIGHTS.md`. The narration claims **no hosted model, no Azure or Foundry run and no open-source licence**; the only Microsoft statement is that the Agent Framework path is verified offline (`docs/FOUNDRY.md`).
