# Judge-access deployment

**Status (2026-10-25): prepared and verified locally; NOT deployed. No public URL exists.**
Rules section 4.8 requires a working project that judges can reach free of charge and without
restriction until the judging period ends (**November 10, 2026, 11:59 PM Pacific**). A repository
checkout does not meet that on its own. Creating the hosting account is a human step; everything
else is ready.

## Provider decision (official documentation, read 2026-10-25)

| Option | Verdict | Evidence |
|---|---|---|
| **Render free web service** (Docker runtime) | **Chosen.** Runs this FastAPI + Vite container; no payment method is mentioned for Free instances | [render.com/docs/free](https://render.com/docs/free): 750 free instance hours per workspace per month; spins down after 15 minutes without inbound traffic (about one minute to wake); no persistent disk; "do not use them for production applications"; Free services are suspended for the rest of the month if bandwidth is exceeded and no payment method is set |
| Hugging Face Spaces (Docker) | Rejected | [Spaces overview](https://huggingface.co/docs/hub/spaces-overview): Docker Spaces "require a paid plan to create" |
| Azure Container Apps (`infra/azure/main.bicep`, `docs/AZURE_DEMO_DEPLOYMENT.md`) | Prepared, **not used**: needs a subscription and cost approval | Template compiles in CI; nothing is provisioned |
| Static hosts (GitHub Pages and similar) | Rejected | Cannot run the FastAPI backend |

Whether Render's Docker runtime is available on the Free plan is not stated on the free-plan page;
the Blueprint reference lists `runtime: docker` and `plan: free` as valid fields together. Confirm
on first apply. If it is refused, the same app also runs on Render's native Python runtime with
`pip install -r backend/requirements-runtime.txt && (cd frontend && npm ci && npm run build)` and
the start command from the Dockerfile.

## What the deployment is

`render.yaml` (repository root) applies the existing `Dockerfile` in `public-readonly` mode:
operator tokens and provider settings are rejected at startup, writes return 403, SQLite lives in
disposable `/tmp`, fixtures are regenerated deterministically after any restart, and
`POST /api/matches/generate` and `POST .../recap` share a 30-per-minute process-wide quota.
`uvicorn --limit-concurrency 32` sheds excess load with 503. Auto-deploy is off so the judged
build is the frozen, tested commit.

On the public demo these work: replay, evidence drawer, One Moment · Three Stories, Fan Lens,
personas and languages, Control vs Chaos, Pass Difficulty, highlight manifest and reel, seeded
replay generation. These are intentionally disabled: Control Room, Data Hub imports and Director
Studio approval (the app now says so on those routes via `GET /api/deployment`).

## Steps for the account holder (about 10 minutes)

1. Sign in at render.com with an account the team controls. Do **not** add a payment method; the Free plan should not need one, and adding one lets overages bill.
2. New → **Blueprint** → connect the public repository `Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi`, branch `main` → apply `render.yaml`. Confirm the plan shows **Free** before approving.
3. Wait for the build (Node build plus Python image). Open the `https://pulse-xi-demo.onrender.com`-style URL Render shows (the exact host is assigned by Render).
4. From a machine that is not the developer's server, run the acceptance suite against that URL:

```powershell
cd frontend
npm ci
$env:PULSE_DEMO_URL = "https://<your-service>.onrender.com"
npx playwright test -c playwright.deployed.config.ts
```

   Expect 4 passed: fixture seek/play/generate, the judge journey (35 s of 4x playback with zero HTTP 429, goal cue, evidence, Three Stories, no console errors), highlight reel plus axe scan, and the public security boundary.
5. Record the URL, the time and the result in issue #25 and in `docs/HACKATHON_SUBMISSION_PACKAGE.md`. Only then is the judge-access gate PASS.

## Known limits (be honest with judges)

- **Cold start.** After 15 idle minutes the first request takes about a minute. Open the URL once shortly before recording or judging; do not rely on an automated keep-alive to defeat the platform's idle policy.
- **Capacity.** Measured on a 12-thread developer machine in this exact mode: one connection 24 ms p50 for a highlights read; about 40 requests/s total at 8-32 concurrent clients; above 32 concurrent connections the server answers 503 by design. Render's free instance has much less CPU, so expect a few concurrent judges to be fine and a crowd to see slow or shed requests. Not measured on Render.
- **Availability through November 10** is not guaranteed by the free plan: 750 hours/month, bandwidth and build-minute caps, and Render may restart services at any time. Check the service on Oct 28, Nov 1 and Nov 9. If it is suspended, restart it or redeploy.
- **No persistence.** State resets on restart. The documented flow does not need any.
- **Shared quota.** Recap and seed generation are metered together across all visitors (30 per minute). Playback now issues about one recap per 10 s per viewer, so roughly four concurrent players fit.
- Not a production deployment, and not a claim of hosted Microsoft services: the demo makes no Azure or Foundry calls.
