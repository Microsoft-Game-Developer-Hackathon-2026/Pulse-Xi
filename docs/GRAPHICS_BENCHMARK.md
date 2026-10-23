# Bounded graphics benchmark

Use a production build and isolated disposable databases. This probe does not
touch the developer's real database or invoke Foundry. From repository root in
PowerShell (activate the existing project venv first):

```powershell
npm.cmd --prefix frontend run build
$env:PULSE_ENABLE_FOUNDRY='false'
$env:PULSE_DB_PATH=Join-Path $env:TEMP ('pulse-graphics-'+[guid]::NewGuid()+'.sqlite')
$env:PULSE_RUNTIME_DB_PATH=Join-Path $env:TEMP ('pulse-runtime-'+[guid]::NewGuid()+'.sqlite')
python -m uvicorn app.main:app --loop app.local_event_loop:create_loop --app-dir backend --host 127.0.0.1 --port 8877
```

In another terminal from `frontend`:

```powershell
$env:PULSE_GRAPHICS_URL='http://127.0.0.1:8877'
$env:PULSE_GRAPHICS_HARDWARE='1'
$env:PULSE_GRAPHICS_EXPECT_GPU='RTX 5070' # Satvik: use 'Iris' for his actual device
npm.cmd run measure:graphics
```

For the optional extended stability session, also set
`$env:PULSE_GRAPHICS_STABILITY_SECONDS='900'` before that command. This adds at
least 900 measured monotonic seconds of camera/profile changes, 2D/3D remounts
every six cycles, five-second observations and checkpointed heap/renderer/error
signals. It cycles all profiles/cameras at the same fixed scenario/event cutoff;
total probe duration is longer than 15 minutes because setup, profile samples,
the existing short idle phase and screenshots are additional. The option accepts
only integers from 0 through 900; zero/unset preserves the short default. Record
actual `stability.elapsedMs`, `stability.observedWorkMs`, cycles and samples.
Completion requires the requested duration spent awaiting browser steps and samples;
JSON checkpoint time is excluded from `observedWorkMs`, but included in total
`elapsedMs`. Missing observations fail without discarding completed samples;
 a failed/interrupted section is
not successful extended evidence. Use the same option on Iris Xe for comparison.

The actual renderer must match the expected physical GPU; software/unknown
renderers fail physical mode. Inventory alone does not establish GPU selection.
For software evidence unset the expected GPU and hardware variables; reports
remain explicitly headless. Stop the temporary server with Ctrl+C afterward.

Each invocation creates `test-results/graphics/run-*/report.json` plus screenshots.
It writes `running` before launching Chromium, checkpoints profiles, and atomically
renames JSON after each update. Completed runs are `passed` only after all steps
and runtime-error checks. Exceptions produce `failed` with end time and the actual
failure. SIGINT/SIGTERM close the browser; a deadline bounds hangs. Signal and
browser-disconnect timestamps are recorded when observable.
The deadline remains five minutes for the default and adds the requested extended
duration for the opt-in session. An OS force-kill/power failure may leave `running`, which is incomplete. Never
promote partial metrics/screenshots or an old success file as this run's result.

The report includes source SHA/dirty flag, OS/CPU/RAM, observable NVIDIA inventory
or null, browser renderer/version, viewport/DPR, verified asset hashes, readiness,
profile draw/triangle/resource counts, request/resource timing and heap samples.
Each profile has five-second warmup and three five-second active free-camera
samples. RAF intervals are browser frame pacing, not GPU execution timing. First
profile includes fresh-browser asset loading; OS/network caches are not purged.
Later profiles reuse the loaded page. GPU utilization/allocated VRAM and forced-GC
leak conclusions are unavailable. It switches all five cameras, profiles, seek and
2D/3D remounts, observes 30 seconds idle, and captures six prescribed viewports.
The default workload is shorter than #34's proposed three 60-second samples and
15-minute soak. Extended mode supplies measured stability time, but its existing
RAF performance samples remain five seconds; it does not claim three 60-second
performance trials or physical Iris Xe acceptance. Human review remains required.

The same commit, built assets, `comeback-1107` scenario, cutoff 3500, profiles and
workload must be used for Satvik's physical Iris Xe comparison. Keep its report
separate from RTX, software rendering and older procedural-only scenes. Preserve
the original raw artifacts; publish only sanitized, reviewed evidence with the PR.
Inspect screenshots visually, and retain missing/corrupt/slow assets, WebGL loss,
reduced-motion and keyboard regressions from the browser suite. The probe alone
does not certify all these behaviors.

Regression command: `node --test frontend/scripts/graphics-report.test.mjs` from
root, after installing the locked frontend packages and Playwright Chromium.
The CLI failure case fails against the original probe because it emits no report.
