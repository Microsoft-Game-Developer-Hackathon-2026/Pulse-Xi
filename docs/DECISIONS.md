# Architecture decisions

Status: proposed for Issue #2 shared review. Main `0beb08d` includes the engine
foundation, trace-read protection and original graphics; live runtime/analysis
integration remains proposed in #53, after separate security integration #52.
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
5. **Separate persistence domains.** Library/runtime schema 2 are different files,
   transactions, migrations, backup allowlists and rollback paths. Atomic commands
   include state/events/receipt/audit/checkpoint. Job progress commits separately
   and recovers with stable command IDs/CAS. Future versions reject; rollback uses
   matching pre-upgrade backups/builds, not down-migrations.
6. **Reuse v1 by projection.** Match/MatchEvent remain 1.0. Adapter preserves
   sequence/IDs and mirrors away x; only 5400-second scenarios fit fixed halftime.
   Private runtime events never silently enter the public library. PR #43's
   authenticated analytics integration has a separate review/testing gate.
7. **Honest observation.** Snapshot replaces state, delta requires cursor agreement,
   gaps recover through authenticated polling/reconnect snapshot. Actor roles/
   stamina and sparse ball/event endpoints exist; continuous tracking/speeds do
   not. Browser workspace/notes are not engine checkpoints or authenticated facts.
8. **Explicit security/provider boundaries.** Fictional data/original assets only.
   Provisioned owner tokens protect runtimes; library reads remain public. Public
   accounts/viewer roles/gateway rate limits are release work. Deterministic facts
   precede optional Foundry opinion; provider configuration never proves inference.
   Trace GET's fail-open default was corrected on main by #45. Command credential
   hardening retains the separate #52 security review and integration gate.
