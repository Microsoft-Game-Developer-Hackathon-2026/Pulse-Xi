# Demo video: production and QA report

Produced 2026-10-26. Output: `artifacts/demo/pulse-xi-final-demo.mp4` (local file, not committed;
sha256 prefix `aded2afb9e84d3bb`). Storyboard and timings: [VIDEO_NARRATION_AND_STORYBOARD](VIDEO_NARRATION_AND_STORYBOARD.md).

## A. The artifact (measured on the final file)

| Property | Result | Tool |
|---|---|---|
| Duration | **110.60 s** (limit: under 120 s) | ffmpeg 7.1 stream info |
| Video | H.264 High, yuv420p, 1920x1080, 16:9, 30 fps constant, about 615 kb/s | ffmpeg |
| Audio | AAC-LC, 48 kHz stereo, about 117 kb/s | ffmpeg |
| File size | 10,259,771 bytes (9.8 MiB), `+faststart` | `ls` |
| Full decode | exit 0, no errors | `ffmpeg -v error -i ... -f null -` |
| Loudness | -15.9 LUFS integrated, LRA 5.6 LU, peak -1.5 dBFS (no clipping) | ffmpeg `ebur128` |
| Black frames | none longer than 0.3 s | ffmpeg `blackdetect` |
| Static holds | title card (0.6-3.1 s) and four 2.5-3.2 s reading holds on static panels | ffmpeg `freezedetect` |
| Captions | 20 cues, last ends at 107.64 s; burned in and as SRT | `assemble.py` |

## B. Production evidence

- **Recorded environments.** Scenes marked "Live" were recorded from the deployed public demo
  `https://pulse-xi-demo.onrender.com` (Render free plan, deployed commit `4770a2d`). The Control Room scene
  was recorded from a local server running the same application code (`main` at `11cf7f0`, later commits to
  `main` are docs and tests), with a disposable database and a throw-away operator token, because operator tools
  are disabled on the public demo by design. The chip in the video states which is which.
- **Data.** Built-in seeded synthetic fixture `comeback-1107` and, for the Control Room, a fresh scenario (seed 98765).
  No real match footage or real-match data.
- **Browser.** Chromium via Playwright with software rendering, 1920x1080, Playwright's screen recorder (VP9, 25 fps), upsampled to 30 fps.
- **Verified journey** (all real clicks): seek, speed, play, goal, evidence drawer, three lenses, persona and language, Control vs Chaos turning point,
  pass inspector, scenario, step, checkpoint, tactic, paired ForkCast, independent verification, highlight reel, final score.
  Every scene script reported zero console errors and zero failed API calls (`problems: []` in each clip report).
- **Optional services:** none used. No Foundry, Azure or model call occurred; none is claimed.

## C. Tools and rights

| Item | Source and terms |
|---|---|
| ffmpeg 7.1 (gyan.dev essentials build, via `imageio-ffmpeg` 0.6.0, BSD-2-Clause wrapper) | Used as a local tool only; not redistributed. The binary is GPL-licensed |
| Narration voice | Windows SAPI `Microsoft Zira Desktop`, offline, no account or paid service. **It is a synthetic voice, not a human voice-over** |
| Fonts | Captions use `Segoe UI Semibold`, a Windows system font, rendered into the video. Overlay graphics use system sans-serif |
| Music, stock media, third-party logos | None. Overlays are original text on dark gradients; "Microsoft Agent Framework" appears only as text in the closing disclosure |
| Playwright, Chromium | Existing project dev dependency |

## D. What was and was not checked

**Checked:** every frame region by contact sheets across the whole timeline (about 45 frames at 0.5-5 s spacing covering all seven scenes, the title card, the end card and
the final fade); caption text and timing against the spoken text and the screen; technical stream, decode, loudness, black and freeze checks above;
the claims in the narration against the code and tests (table in `artifacts/demo/pulse-xi-narration.md`).

**Defects found and fixed during QA:** the replay scene auto-scrolled away from the scoreboard (fixed); the recap the audience beat changes was off-screen (zoom removed);
the reel was offset and the chip covered its score (zoom and container fixed, chip removed); a form-feed escape bug silently dropped one caption (fixed, 20 of 20 cues now present);
captions covered the reel's evidence line (smaller, lower caption); no end fade (added).

**Not done:** a human has not watched the final file start to finish with sound, so pronunciation, pacing and the overall audio feel are unreviewed.
Caption timing inside each segment is proportional to sentence length, not word-aligned. The Control Room scene is a local run, not the public URL. No upload has occurred.

## E. Findings worth knowing

- On the free host a recap or metrics request takes about 350-370 ms from this machine against about 20-26 ms locally, so the "loading recap" moments in the audience beat are real and judges will see them.
- The first request after idle took about 24-36 s (cold start). Warm the URL before recording or judging.

## F. Reproduce

```powershell
python -m pip install imageio-ffmpeg
cd frontend; npm ci; npm run build; cd ..
# local server with a throw-away operator token for the Control Room scene
$env:PULSE_RUNTIME_TOKEN="<random 32+ chars>"; $env:PULSE_RUNTIME_DRIVER="1"; .\scripts\start.ps1
powershell -File scripts/demo_video/synth_narration.ps1
node scripts/demo_video/make_overlays.mjs
foreach ($s in 'replay','evidence','audience','intelligence','close') { node scripts/demo_video/record.mjs $s --base https://pulse-xi-demo.onrender.com }
node scripts/demo_video/record.mjs reel --base https://pulse-xi-demo.onrender.com
$env:DEMO_RUNTIME_TOKEN=$env:PULSE_RUNTIME_TOKEN; node scripts/demo_video/record.mjs control --base http://127.0.0.1:8000
python scripts/demo_video/assemble.py        # writes artifacts/demo/pulse-xi-final-demo.mp4 and .srt
python scripts/demo_video/review_frames.py 5,30,60,90 sheet.png   # visual spot check
```

## G. Publication steps still required (not done)

1. Watch the MP4 once with sound; if anything is off, edit `scripts/demo_video/narration.json` or `timeline.json` and rerun `assemble.py`.
2. Upload to YouTube, Vimeo, Facebook Video or Youku as **public**; attach the SRT as captions if the platform allows.
3. Confirm logged-out playback and that the platform shows a length under 2:00.
4. Paste the public URL into issue #25 and the submission form. Until then the video requirement is **not** met.
