# PULSE XI — MASTER IMPLEMENTATION PROMPT FOR CODEX

You are the lead principal full-stack engineer, applied football analytics specialist, Azure solution architect, agentic AI engineer, data engineer, product designer, security reviewer, test engineer, and technical writer for a NEW project called **PULSE XI: The Football Intelligence Operating System**.

## Mission
Build a working, well-tested, original, visually excellent entry for the Microsoft × Premier League **Inside the Game: Developer Hackathon 2026**. The product must transform **synthetic, football-realistic match events** into explainable live intelligence, tactical patterns, machine-readable time-synchronized broadcast overlays, multilingual commentary, personalized fan/analyst modes, and automated recaps. It must be a REAL FUNCTIONING web application, not a screenshot, mock-only dashboard, placeholder API, or static animation. Prioritize reliable local operation before Azure deployment.

Official challenge/rules: https://aka.ms/insidethegame and https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md . Review these sources if network access is allowed, and treat official rules as authoritative. Registration closes Oct 20 2026 at 12:00 Pacific; submissions close Oct 27 2026 at 23:59 Pacific. The user is working in Asia/Kolkata. Confirm updated rules before final submission. The project must be newly built, with a public GitHub repo, a <2-minute real functional demo video and a publicly accessible working demo for judges. NO unlicensed match footage, copyrighted music, real Premier League event feed or unauthorized clubs' logos. Invent fictional teams and synthetic identities for demo content. Label all invented matches "Synthetic simulation".

## Execution contract — READ CAREFULLY
1. Work in the current/new project folder. If an existing workspace is present, inspect first; never delete or overwrite valuable files without cause. Initialize a new monorepo if empty. Implement changes rather than merely describing them.
2. Do not ask broad planning questions. Make sensible choices, record assumptions in docs/DECISIONS.md, and progress through phases. Ask ONLY at actual credentials/paid deployment/privacy boundaries.
3. Zero mandatory paid APIs and zero mandatory cloud credentials for LOCAL DEMO. The application must run end-to-end locally with deterministic event generation, real computed analytics, template-based verified narratives when an LLM is unavailable, and clearly labeled LLM-unavailable state. This local fallback must not be misrepresented as live AI model inference. Provide a Microsoft Foundry integration that genuinely works when configured and demonstrate/document a real invocation for submission.
4. Use the Microsoft ecosystem intentionally, not superficially: Microsoft Foundry as primary LLM backend; Microsoft Agent Framework for actual orchestrated collaboration; Azure Static Web Apps for frontend deployment and Azure Container Apps for Python API; GitHub Actions for CI; optional Azure Speech for voice and optional Microsoft Fabric for batch analytics if provisioning is feasible. These integrations must be functional or clearly marked optional/not configured, never fake or hardcoded badges.
5. Work in vertical slices. After each phase: run relevant tests, verify UI, add clear docs, report what works, what failed, blockers, next phase. Check in code at meaningful milestones if git configured; NEVER make fake claims about running tools, cloud deployments, tests or LLM calls.
6. Do not install enormous ML models or costly GPU infrastructure. No speculative computer vision tracking: video auto-eventing is stretch only if a licensed synthetic source and an actual robust tracking pipeline exist. Synthetic football-pitch animation is NOT equivalent to video-based event extraction.
7. No hardcoded secrets, no client-side API keys, no unbounded rate calls, no hidden costs; read keys only server-side from environment, provide .env.example, and default Azure deployment to opt-in. Provide clear deletion/cleanup scripts and cost warning. Never trigger paid deployment or spending without explicit approval.
8. Keep it reasonably simple and demonstrable by one developer before Oct 27, 2026. The quality of the core journey outweighs quantity of cosmetic features.

## Central product concept
One simulated match, many simultaneous explainable perspectives. A time-aligned master event feed drives five continuous steps: INGEST → INTERPRET → EXPLAIN → RENDER → PERSONALIZE. This same data powers a broadcast director, a tactical analyst dashboard, a casual-fan match view, player-focused mode, a multilingual recap, and the Match Time Machine replay. Distinctive named innovations:

- **ProofTrail:** Every major factual narrative claim links to event IDs, time windows, calculations, evidence provenance, and appropriate confidence. A click opens a proof drawer showing match events and intermediate statistics. Distinguish measured synthetic facts, analytics-derived inferences, model opinions and hypothetical scenarios. Never have LLM invent numeric metrics.
- **Director AI:** A rules+agent workflow selects moments with editorial importance, checks claims, schedules overlay cues on the simulated match clock, applies duration/pacing/safe area/priority rules, and emits machine-readable overlay JSON suitable for OBS or a production graphics renderer.
- **FanDNA:** Same grounded insight presented for Casual Fan, Tactical Analyst, Broadcaster and Player Focus. Personalize by favorite synthetic team/player, language (English, Spanish, Hindi to start), reading level, density, and optional voice. Actual content should materially differ between modes, not merely relabel cards.
- **Match Time Machine:** pause, resume, seek, step frame/event, switch speed (0.5x, 1x, 2x, 4x), navigate critical moments; replay state must be reconstructed deterministically and synchronized with overlays and narratives. Refresh should restore selected match and sensible playback state.
- **ForkCast What-If Lab:** adjust fictional scenario parameters such as press intensity, defensive line, attacking width, substitutions or passing directness; rerun a seeded simulation from chosen minute and compare distributions across multiple Monte Carlo rollouts where computationally feasible. Always label "hypothetical synthetic scenario" and show assumptions/uncertainty; do NOT claim causal certainty, real forecasts, or actual team recommendations.

## Stack and structure
- Frontend: React + TypeScript + Vite + Tailwind CSS + shadcn/ui, accessible Radix primitives, lucide-react icons; Motion for small interactions, Recharts for time series, custom responsive SVG/Canvas for football pitch, passing network and overlays. Do not introduce Next.js unless strong justification. No unauthorized sports logos or external real-match imagery.
- Backend: Python 3.11+ FastAPI, Pydantic v2, asyncio WebSockets, SQLAlchemy, SQLite by default; PostgreSQL adapter if cloud deployment needs it. Use Polars/Pandas/NumPy only where they improve analytics. pytest and Ruff.
- Contracts: Pydantic models produce documented OpenAPI and checked frontend TypeScript types. Zod runtime schema validation where valuable. Use event_id, match_id, source_type, schema_version and UTC ingest timestamp plus logical match clock in every event.
- Agents: Microsoft Agent Framework with foundry-backed clients (verify latest official SDK examples rather than guessing). Keep an injectable `ModelProvider` interface: MicrosoftFoundryProvider, OptionalLocalProvider, and DeterministicNarrativeFallback. Separate deterministic analytics from AI narrative synthesis. LLM calls only for salient candidate moments or on-demand recap, not every raw event.
- Infrastructure: `frontend/`, `backend/`, `data/`, `infra/`, `scripts/`, `tests/`, `docs/`, `.github/workflows/`; Docker Compose for backend/local dependencies when sensible; local setup without Docker also documented; GitHub CI; Azure provisioning templates (Bicep or azd). Avoid expensive always-on Azure resources by default.

## Core domain/event schema
Create typed models and versioned JSON schema for:
- Match: match_id, synthetic=true, seed, teams, roster, formations, event_source, duration, simulation config, kickoff timestamp or none, score and current phase.
- Team and player: fictional unique IDs, names, roles, formation position, attributes with documented distributions, substitution state.
- MatchEvent: event_id, match_id, sequence, match_second, period, team_id, actor_id, recipient_id(optional), event_type (kickoff, pass, carry, shot, goal, save, tackle, interception, pressure, recovery, turnover, clearance, foul, card, substitution, halftime, fulltime), outcome, normalized pitch coordinates start/end, possession_id, contextual qualifiers, provenance="synthetic-generator", optional speed_mps, ball_speed_mps, shot_speed_mps only if actually derivable or generated with documented method, generated_at_utc.
- MatchState: score, possession, teams/players on pitch, rolling windows, last event, spatial zones, pressure trend, stamina approximation if computed, passing accuracy, dangerous sequences, momentum proxy with methodology.
- Insight: insight_id, category, match_second, factual_claims, supporting_event_ids, derived_metric_ids, explanation, evidence_window, uncertainty, priority, verification_status, hypothesis=false, timestamps.
- OverlayCue: id, match_id, trigger_match_second, show_duration_seconds, priority, overlay_type, text, metrics, evidence references, locale, persona, safe_area, animation in/out, and version. JSON must remain valid without frontend.
- Scenario: scenario_id, source_match_id, fork_second, random_seed, parameter_changes, n_runs, outcome_statistics, confidence_intervals or quantiles, scenario_type="hypothetical", original_comparison.
Implement migrations, serialization tests, examples and a schema contract doc. Support idempotent ingest and replays despite out-of-order or repeated event deliveries.

## Synthetic data: realism is essential
Design a reproducible seeded generative simulator with a simplified spatial/possession state machine. The simulator should generate coherent possessions and realistic match structure, not arbitrary random unconnected events. Use configurable team tactics, passing preferences, zones, transitions, fatigue/pressure proxy, counterattacks, high presses, match clock, shot events and goal outcomes. Keep invariant checks: periods/time ordering, every referenced actor in proper team, sane pitch coordinates, mutually consistent possession and score, outcomes consistent with event types, no post-final-whistle events. Tune distributions to be plausible but never claim calibration to Premier League data unless licensed and verified; include methodology, assumptions, known limitations. Provide at least 3 deterministic narrative-rich seeds, including comeback, high press, late winner, plus one configurable custom simulation. Allow downloadable JSON/JSONL sample events and deterministic import of a compatible user-provided synthetic dataset (CSV/JSON validation, size limit, malicious input defense). Guarantee one seeded match reliably shows a revealing tactical turning point in the 2-minute demo. Include a replayable fixture with golden expected outputs.

## Deterministic analytics before language generation
Implement and test: completion rate, pass distance, pass difficulty proxy with exact formula, possession sequence lengths, shots, goals, shot quality proxy clearly not a trained xG model unless trained/calibrated, recoveries, final-third entries, turnovers, pressing proxy, dangerous turnovers, successful defensive exits, rolling 5/10 minute windows, passing network, spatial event map, player contribution trends and key momentum swings with threshold+hysteresis/debounce to avoid insight spam. Calculate all measurements from the event stream. If tracking samples and timestamps are absent, do not claim measured player speed/shot speed. Confidence score must distinguish data completeness from model prediction confidence; never present arbitrary percentages as calibrated probabilities.

## Multi-agent orchestrator: real job separation
Use a sensible multi-agent workflow from Microsoft Agent Framework with inspectable traces, shared typed state, explicit tools/inputs/outputs, and deterministic fallbacks:
1. Tactical Analyst — receives computed match evidence; proposes tactical explanations; does not calculate unknown facts.
2. Story Editor — identifies broadcast-ready narrative, milestone and player-performance storyline.
3. Evidence Auditor — validates every factual number/team/player/event cited against authoritative event/analytics store, requests revision or rejects unverifiable stories. Do not rely only on another LLM for validation; implement rule-based claim checking as gate.
4. Broadcast Director — applies priority, cooldown, suppression during busy periods, cue timing, expiration, accessibility and overlay layout constraints.
5. Fan Personalizer + Translator — transforms an APPROVED evidence packet for persona, club/player focus, language and reading density, preserving metrics and evidence references. If translation provider absent, support honest limited deterministic/localized templates; don't fabricate multilingual completeness.
Only run AI where useful. Simultaneous Tactical/Story proposal → Audit → Director → fan personalization is one meaningful workflow; checkpoint it and trace actual handoffs. Handle 429/timeouts, circuit breaker, retries with backoff, deduplication, caching, schema validation, rate and token budgets. Expose an Agent Trace inspector in the UI or admin tab. Ensure the platform works if Foundry unavailable, with explicit "Verified rule-based narrative" badge instead of pretending an agent generated it. Provide evaluation harness for hallucination rate, citation accuracy and narrative quality on fixed fixtures.

## End-to-end visual product
Implement a striking, professional, original 16:9 dark sports-production look (deep charcoal, restrained electric cyan/coral accents, fine typography; avoid copying actual network branding), strong mobile responsive state and keyboard accessibility. Mandatory functional screens:
1. **Match Command Center** landing with synthetic match selector, status, scoreboard, timeline, replay controls, real-time feed, match clock, live score, pitch event replay, highlight cue carousel, event counters and agent health.
2. **Broadcast Studio** 16:9 output preview, transparent overlays on a synthetic pitch / authorized placeholder visual, cue queue, preview vs program, safe margins, JSON cue preview/download, countdown, producer approval/override, OBS browser-source-safe route.
3. **Tactical Lab** pitch heatmap, passing networks, evolving possession/pressure proxy, selected time window, player comparison, evidence-backed insight cards, ProofTrail drawer.
4. **FanDNA** working persona switch, fictional team/player selector, English/Spanish/Hindi where available, narrative density, favorite metric, meaningful changes to presentation; player-focused narrative timeline.
5. **ForkCast** fork minute, editable tactical controls, seeded scenario runs, uncertainty visualization, comparison to baseline, "synthetic hypothesis" labels.
6. **Match Time Machine** either dedicated route or integrated replay mode: pause/seek/playback controls, reliable state reconstruction and synchronized AI overlays.
7. **Recap Room** automatically compiled match story, key moments, event-linked fact cards, bilingual/multilingual copy where configured, speech button when provider configured, downloadable JSON + Markdown recap.
8. **Engineering / Trace** documented system status, provenance, latency, ingestion health, agent DAG, failures and cost estimates (no fake measurements).
Prioritize core 1,2,3,4,7,8 before fully extending 5 or polishing extras. All components must show real data from backend; no hardcoded beautiful statistics. Empty and loading/error states should be good. Visual cues must correspond to in-match time and correct current score.

## Explicit API and streaming requirements
Suggested routes (change as needed and document):
GET /health; GET /api/matches; POST /api/matches/generate; GET /api/matches/{id}; GET /api/matches/{id}/events?cursor=...; GET /api/matches/{id}/state?at_second=...; GET /api/matches/{id}/insights; GET /api/matches/{id}/metrics; GET /api/matches/{id}/overlays; POST /api/insights/{id}/explain; POST /api/matches/{id}/recap; POST /api/scenarios; GET /api/scenarios/{id}; GET /api/agent-traces; GET /api/export/{match_id}; WS /ws/matches/{id}. Provide strict payload validation, status/error responses, cancellation and authentication to admin functions as appropriate. Do not expose arbitrary synthetic generator compute or LLM costs to unrestricted public users. Choose an appropriate local-only replay clock authority and cloud single/multi-client consistency model. Provide reconnection, snapshot+delta, sequence IDs and event stream dedupe.

## Performance/SRE/security
Targets, measured locally rather than claimed: smooth 60fps pitch animation on a typical laptop where practical; near-immediate deterministic stat calculations for individual events; reasonable streaming latency; no full agent inference in event ingestion hot path. Instrument event-to-stat, event-to-overlay, LLM latency, validation failure, false insight rates, narration claims unsupported, WebSocket reconnection, and scenario runtime. Provide pytest property/invariant tests, fixtures, API integration tests, WebSocket tests, frontend tests (Vitest/Testing Library), 2-3 Playwright end-to-end flows, screenshot smoke test where environment permits, GitHub Actions, Ruff, TypeScript strict mode, no secrets in public repo, dependency audit, rate limits, CORS policy, safe HTML/text rendering, input filesize limits, and clear error boundaries. DO NOT imply production SLA or real Premier League validation.

## Azure integrations and deployments
1. Develop/test entirely locally first.
2. Integrate actual Microsoft Foundry SDK/provider behind server-only ENV; use Microsoft Agent Framework using current documented APIs; log a trace of at least one genuine hosted model invocation when credentials present. Provide fallback templates without claim of same AI capabilities.
3. Add optional Azure Speech F0 neural TTS if accessible, with text fallback and accurate language support. Do not introduce generated clone voice or unauthorized impersonation.
4. Configure Azure Static Web Apps Free for frontend if eligible, Azure Container Apps Consumption for backend, with cost planning, scale-to-zero trade-offs, API URL settings, CORS, secure ENV, healthcheck and clear public URL. Beware compute/network/storage/observability/Foundry inference charges and quota restrictions.
5. Optional Microsoft Fabric 60-day trial for batch analysis and an illustrative Lakehouse / semantic reporting flow ONLY if trial can be provisioned; the app must not depend on it. Provide honest integration status and screenshots of real runs if used.
6. Write infrastructure template (Bicep/azd or CLI deployment scripts), separate explicit deployment command, and cleanup command. Do not actually provision/spend money without user authorization. Never claim cloud services are integrated until integration tests with user-configured Azure resources pass.

## Deliverables
- Running source code in clearly laid-out monorepo, 1-command Windows-friendly local startup script (plus manual commands) and pinned dependencies.
- Three polished seeded end-to-end demo matches, evidence graph with source IDs, interactive studio and fan experiences.
- Tests + CI pipeline, example inputs, JSON contract and explanation of all derived metrics.
- README with architecture Mermaid diagram, prerequisite setup, dev instructions, screenshots (actual app), runbook, design decisions, limits, licensing/attribution and Azure hosting diagram.
- docs/DEMO_SCRIPT.md for <120 second honest screen recording showcasing ACTUAL functioning application, not generated substitute footage; plan: 0-12 hook, 12-35 ingest + shift, 35-58 ProofTrail, 58-82 FanDNA multilingual, 82-102 Broadcast Studio timed cue, 102-115 scenario or recap + Microsoft tech proof.
- docs/SUBMISSION.md with 100-200 word pitch, tech stack proof, category positioning (Grand Prize + Best Multi-Agent, or Foundry, as appropriate), public repository, hosted test link, test instructions and cloud status.
- docs/RISK_REGISTER.md, docs/DECISIONS.md, docs/COSTS.md with optional/real costs, docs/QUALITY_REPORT.md with measured metrics.
- docs/PROJECT_STATUS.md with phase complete/partial status, no invented checkmarks.

## Iterative roadmap — implement rather than over-plan
PHASE 0: Inspect workspace, verify current versions, set up project scaffolding, typed schemas, design tokens, README, task tracker. Establish 'one command starts demo' goal.
PHASE 1: Real seeded synthetic football state machine, event bus, event persistence, deterministic analytics, tests. Expose REST and WebSocket; use at least 3 golden seeds.
PHASE 2: Gorgeous responsive Match Command Center with real live replay, pitch animation, score/timeline, stat panels, rewind/replay, browser-refresh-safe controls. E2E flow works.
PHASE 3: Evidence extraction/ProofTrail. Rule-based explanation rendering must work even without Foundry.
PHASE 4: Actual Microsoft Agent Framework + Microsoft Foundry integration, Evidence Auditor, traces and retry/fallback. Never fake. Add evaluated demonstration example.
PHASE 5: Broadcast Studio overlay engine with timing, machine-readable cue schema, synchronized overlay preview and export, optional OBS route.
PHASE 6: FanDNA distinct casual/analyst/player views, language handling, recap generator with citations to events, optional Azure Speech.
PHASE 7: ForkCast seeded hypothetical scenario engine with explicit uncertainty; optional Fabric analytics.
PHASE 8: Run tests, eliminate placeholders, keyboard/responsive polish, Docker/CI, Azure deployment preparation, honest security/cost docs, test external judges' route, under-2-minute real demo, public repository and submission checklist.

TIME MANAGEMENT: the project must be ready to submit by Oct 27 Pacific. Core complete vertical slice by Oct 20; Azure and Foundry integration by Oct 23; tests/demo by Oct 26. Reserve final day for submission and fixes. If behind, cut ForkCast UI depth and extra visual polish before cutting core, ProofTrail or functional Foundry integration.

## First Codex response/action
1. Print a compact execution plan (up to 12 lines) and concrete stack choices; list only genuine external blockers.
2. Inspect cwd/OS/dependency versions; create/reuse project; initialize structure and documentation.
3. BEGIN IMPLEMENTING PHASE 1 in this very run. Do not stop at a plan. Write the event schema, seeded simulator, analytics starter, working FastAPI endpoints and minimal tests and run them.
4. Show precise file paths, commands and actual test results; say what's next. Continue implementing phases as context permits; if you cannot finish all, leave runnable integrated code and a precise task backlog, not superficial placeholders.

QUALITY BAR: reliable working product + transparent evidence + genuinely useful Microsoft agents + an exceptional live demo. Never promise contest victory. Don't claim outputs, demos, predictions, or deployments you haven't actually validated.
