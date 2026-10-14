# PULSE XI — Architecture, Release Plan and Setup

Project: **PULSE XI — The Football Intelligence Operating System**
Tagline: *One match. Infinite perspectives. Every insight explained.*

## What to ship
A responsive web application with a deterministic synthetic football match simulator. A single event feed drives real statistics, explainable moment cards with source event IDs, a synchronized 16:9 broadcast overlay studio, distinct fan/analyst/player-focused views, multilingual recap outputs, and a traced Microsoft Agent Framework + Microsoft Foundry orchestration path. Optional tactical what-if simulator, voiceover, and Fabric batch analytics.

## The crucial five-stage pipeline
INGEST synthetic passes/shots/tackles/pressures/meta → INTERPRET with deterministic calculations → EXPLAIN grounded events with clear evidence → RENDER time-synced machine-readable overlay JSON → PERSONALIZE persona/player/team/language.

## Authoritative architecture
```
Synthetic match state machine (seeded, documented distributions)
  -> validated append-only event feed (idempotent event IDs)
  -> event store / replay snapshots
  -> deterministic metrics, spatial analysis, timeline
  -> evidence graph and candidate highlights
  -> multi-agent Foundry workflow: Tactical Analyst + Story Editor
     -> deterministic Evidence Auditor / LLM-assisted verifier
     -> Broadcast Director
     -> FanDNA translation / personalization
  -> broadcast overlay cue JSON + user-facing narratives + recaps
  -> React SPA through FastAPI REST/WebSockets
```

## Product screens
1. Match Command Center: synthetic match selector, scoreboard, pitch replay, clock, status, timed feed, metrics.
2. Tactical Lab: heatmaps, passes, pressure/possession rolling windows and ProofTrail.
3. Broadcast Studio: preview/program modes, machine-readable cue timeline, clean 16:9 overlays.
4. FanDNA: Casual / Analyst / Player and club/player/language preferences.
5. Match Time Machine: pause, seek, step, speed and exact state reconstruction.
6. Recap Room: supported-story auto-recap and copy/export.
7. Agent Inspector: traces, validation, latency, provenance, health.
8. ForkCast optional: seeded scenario and uncertainty chart.

## Suggested folder tree
```
pulse-xi/
  frontend/              # React + TS + Vite + Tailwind
  backend/
    app/
      api/               # FastAPI and WebSockets
      domain/            # Pydantic event/state contracts
      simulation/        # deterministic seeded match state machine
      analytics/         # metrics, momentum proxy, event provenance
      agents/            # Foundry provider, Agent Framework orchestration
      narrative/         # ground-truth validation, i18n, summaries
      overlays/          # timed broadcast cues and JSON schema
      persistence/       # SQLite and optional PostgreSQL
      scenarios/         # optional hypothesis simulator
    tests/
  data/fixtures/         # 3-4 fictional deterministic match seeds
  infra/                 # opt-in Azure provisioning templates
  scripts/               # one-command startup, health tests, cleanup
  docs/                  # design, methodology, demo, submission, cost
  .github/workflows/     # lint/build/test CI
```

## Timebox (India)
- Oct 14: install/check Node, Python, Git, Docker optional, Azure CLI, VS Code + Codex; create repo; scaffold.
- Oct 15-17: schema, synthetic realistic generator, quality tests, analytics and REST/WS.
- Oct 18-19: live pitch and main UI, timeline, replay, evidence clickthrough.
- Oct 20-21: verified Microsoft Foundry + Agent Framework path, agent traces, narrative verification.
- Oct 22-23: overlay studio, FanDNA modes, multilingual recap.
- Oct 24: optional scenario and TTS, stronger UI polish.
- Oct 25: deployment on Azure, cost checks, browser and responsive tests.
- Oct 26: record true live 2-minute demo, finish docs, public repo readiness.
- Oct 27 (PDT): review submission and verify links BEFORE deadline Oct 28 12:29 PM IST. Reserve margin; don't plan to submit at the last minute.

## Microsoft services and actual cost stance
- Microsoft Foundry models/agents: use genuine endpoint/model only after subscription and quota verification; inference may incur usage charges even if project creation is free. Use `azure-ai-projects` 2.x and `agent-framework-foundry` consistent with current docs.
- Azure for Students: if eligible, typically $100 promotional credit; verify region, access, quotas and credit remaining. Not a universal free pass for all resources.
- Azure Static Web Apps Free: suitable for React frontend, subject to limits.
- Azure Container Apps Consumption: grants 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests per subscription monthly; external costs can still occur.
- Microsoft Fabric: optional 60-day trial only if enabled on account; avoid critical dependency.
- Azure Speech: optional for languages and TTS, verify F0 tier quotas.
- Higgsfield: optional for licensed original opening artwork / cinematic title; never substitute AI-generated movie scenes for footage of running application, or pretend video analysis derived from generated footage. Check credits/licensing before using.

## Local prerequisites (Windows PowerShell)
- Install Git, Node.js current LTS, Python 3.11+, VS Code and Codex CLI; Docker Desktop recommended not required for app to run locally.
- Check: `node --version`, `npm --version`, `python --version`, `git --version`, `codex --version`.
- Start from an empty project folder and execute the master prompt in Codex CLI. Codex should provide actual development scripts; do not assume them before they're created.
- For Azure use `az version`, `az login` only when ready; do not place API keys in client source or GitHub.
- `gh auth login` when ready to publish the repository; do not publish until license/data checks pass.

## Model/evidence and product honesty rules
- Synthetic data cannot prove Premier League real-world statistics.
- 'Why' means evidence-based tactical explanation (association/structure), not ground-truth causation.
- Counterfactuals are hypothetical scenarios and should show variation/uncertainty.
- xG, player speed, shot speed etc must have defined methods; don't show unsupported metric.
- Data completeness confidence must not masquerade as calibrated confidence in an AI model.
- Clear badge distinguishes data-backed rule-based output vs actual Foundry model output.
- Real match footage, sponsor/club logos, copyrighted music require permission and are not supplied by organizers.

## Competition checklist
- Newly built during registration period, original assets, synthetic football events.
- Five-stage pipeline: ingest, interpret, explain, render, personalize.
- Microsoft technologies genuinely integrated and demonstrable.
- Working publicly accessible demo, with any login credentials supplied to judges.
- Public GitHub repository with reproducible setup and code.
- English short pitch, architecture, evidence, tech stack, and a less-than-two-minute REAL screen recording uploaded to an approved public provider.
- Validate submit by 27 Oct 2026 23:59 Pacific (28 Oct 12:29 IST).
- Keep hosted demo freely testable through end of judging period.

## Official resources
- Hackathon: https://aka.ms/insidethegame
- Official rules: https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md
- Microsoft curated learning: https://github.com/microsoft/insidethegamehackathon/blob/main/RESOURCE%20PLAYLISTS.md
- Microsoft Foundry SDK: https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview
- Agent Framework: https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/
- Azure for Students: https://azure.microsoft.com/en-in/free/students/
- Azure Static Web Apps: https://learn.microsoft.com/en-us/azure/static-web-apps/plans
- Azure Container Apps pricing: https://azure.microsoft.com/en-us/pricing/details/container-apps/
- Fabric trial: https://learn.microsoft.com/en-us/fabric/get-started/fabric-trial
