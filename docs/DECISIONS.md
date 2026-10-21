# Architecture decisions

Status: implementation-aligned. Main `d1d099e` integrated #53, including runtime,
architecture, analysis and command hardening. The Issues #2-#5 completion revision
adds a scenario archive/metadata layer; its acceptance uses the expressly authorized
self-review plus reproducible automated checks, without claiming teammate approval.
[AUTHORITATIVE_ENGINE](AUTHORITATIVE_ENGINE.md) is the shared
specification/model/API/test map; [LIVE_SANDBOX](LIVE_SANDBOX.md) supplies examples.
The blueprint/master prompt express intentions rather than current contracts.

1. **One live authority.** Pure engine transitions advance integer seconds;
   runtime SQLite owns committed EngineState. Browser playback owns only recorded
   event cutoffs. Resume permits advance; a durable run schedules it. Reads,
   rendering and historical inspection never tick a live match.
2. **Separate simulation modes.** Legacy fixtures use Python random.Random(seed)
   (Mersenne Twister), scripted goal schedules and floating-point geometry. The
   zone engine uses four owned SHA-256 counter streams and integer arithmetic.
   Their seeds/histories are not interchangeable or calibrated predictions.
3. **Complete continuation.** Snapshot includes resolved scenario, clock/lifecycle,
   actors/tactics, score/ball/possession, every RNG key/counter, pending queue,
   next decision/order, revision/events/interventions. Seed-only restoration is
   insufficient. Restore creates a child with saved lifecycle and ancestry;
   the parent never rewinds and inherited operation IDs stay reserved.
4. **Stable ordering/bytes.** Tactics precede restarts, boundaries and decisions;
   insertion/emission order breaks ties. Sorted compact ASCII JSON with explicit
   defaults/nulls defines engine hashes; audit UTC is excluded. Identical supported
   build/inputs reproduce. Different command batching can alter state revisions/
   hashes while preserving gameplay. Cross-platform parity needs actual evidence.
5. **Separate persistence domains.** Library schema 2 and runtime schema 3 are different files,
   transactions, migrations, backup allowlists and rollback paths. Atomic commands
   include state/events/receipt/audit/checkpoint. Job progress commits separately
   and recovers with stable command IDs/CAS. Future versions reject; rollback uses
   matching pre-upgrade backups/builds, not down-migrations.
6. **Reuse v1 by projection.** Match/MatchEvent remain 1.0. Adapter preserves
   sequence/IDs and mirrors away x; only 5400-second scenarios fit fixed halftime.
   Private runtime events never silently enter the public library. Authenticated
   analytics integration reached main through #53; short scenarios keep the adapter limit.
7. **Honest observation.** Snapshot replaces state, delta requires cursor agreement,
   gaps recover through authenticated polling/reconnect snapshot. Actor roles/
   stamina and sparse ball/event endpoints exist; continuous tracking/speeds do
   not. Browser workspace/notes are not engine checkpoints or authenticated facts.
8. **Explicit security/provider boundaries.** Fictional data/original assets only.
   Provisioned owner tokens protect runtimes; library reads remain public. Public
   accounts/viewer roles/gateway rate limits are release work. Deterministic facts
   precede optional Foundry opinion; provider configuration never proves inference.
   Trace GET's fail-open default was corrected on main by #45. Command credential
   hardening is present on main through #53, even though #52 remains open.

9. **Provenance outside simulation state.** ScenarioConfig/Scenario/core hashes
   remain unchanged. Runtime schema 3 adds owner-scoped scenario_metadata only;
   pre-upgrade creation times stay unknown. scenario-archive/1 embeds the existing
   Scenario plus explicit RNG provenance and creation UTC. Import rebuilds identity;
   the first stored record wins on identical imports. Timestamps are unsigned
   provenance, never an input to transitions or a proof of authorship.
