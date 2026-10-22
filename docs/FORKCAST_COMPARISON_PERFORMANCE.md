# Verified ForkCast comparison reuse

## Defect and scope

The Windows maximum-history acceptance probe exceeded the existing90-second
comparison-table wait on unchanged maind19a898 and the audit candidate. Linux CI
passed the same case, so this is a local resource/performance failure rather than
proof of universal incorrect results.

Before this change, comparison() called bundle(), which reconstructed captured
histories, calculated a comparison and independently verified the bundle. Then
comparison() reconstructed all histories and calculated the same result once
more. That final pass is redundant after verification of the comparison hash.

## Correction

A private _verified_comparison() returns the bundle and the calculation from one
captured, owner-scoped request only after verify_bundle() succeeds. Public bundle()
and comparison() expose their respective outputs. No global or cross-request
cache, credentials, owner bypass or new serializer is introduced. All independent
verification, tamper rejection, ancestry, input/parent boundary and comparison-hash
checks remain. Engine transition/RNG/model/serializer files and analytical formulas
are unchanged. The verifier adds request-local common-prefix proof reuse as
described below.

Calculation now reconstructs only trial suffixes from the immutable checkpoint.
The independent verifier reconstructs the common prefix from kickoff once per
bundle; it replays each distinct branch suffix from that independently computed
state. Later branch prefix records, scenario and ancestry must exactly match the
verified proof, or full kickoff replay is used. No claimed final state is trusted. Each verified last ancestor must match parent session/checkpoint,
revision and state hash before that parent is reused in verification calculations.
A forged early prefix operation remains rejected. apply_command is copy-on-write,
so each trial leaves the shared source checkpoint unchanged.

The new regression first failed against original main with the explicit
post-audit fourth-replay assertion. It passes on the candidate, as do69 focused
runtime/reproduction tests. Both independent committed example verifiers pass.

## Versioned source fingerprint

The experiment implementation hash intentionally includes experiments.py. Its
fingerprint changes when these files change. The source fingerprint also covers
manifest.py, so verifier changes update the build fingerprint by design. Engine
transition code and canonical hash algorithms are unchanged. Both committed
examples update **only** their build/experiment fingerprint fields.
Its events, operations, state/event hashes, inputs and comparison
hash are byte-equivalent as parsed values. No golden result was regenerated or
changed to hide divergence. As with the existing contract, archived bundles must
be verified with their matching implementation version.

## Measured workload

Reproduce:

```powershell
python scripts/benchmark-forkcast-comparison.py --output .codex-progress/comparison.json
```

Windows11, Python3.13.14, Intel i7-1355U class processor (raw CPUID in JSON),
seed7, duration1800, checkpoint1200,2 paired trials,300-second horizon,
concurrency1, three sequential in-process samples per revision. Temporary SQLite
stores; no HTTP/provider calls or personal data. Background load was uncontrolled.

| Measurement | Original main | Candidate 743916c |
|---|---:|---:|
| Total replayed command transitions per comparison | 150 | 35 |
| Independent verifier transitions | 30 | 15 |
| Measured median ms (3 samples only) | 6060.74 | 346.61 |
| Comparison hash | c071ffb03edad0d6dedc86dcff76f1f0cebd3fce5ace4c5054b4fce5236e075d | identical |

[Raw baseline](benchmarks/forkcast-reuse/before.json) and
[raw candidate](benchmarks/forkcast-reuse/after.json) preserve every observation.
The repeatable result is76.7% fewer replay transitions. Independent proof work reuses only an
identical, already-proven prefix; all claims still undergo validation. The observed94.3% median reduction
is a small, high-variance local sample, not a P95/production improvement guarantee.
The original counter omitted storage.manifest_at's own replay; final before/after
profiles instrument all three locations. The current-boundary fast path captures the
current trial boundary through storage.manifest()'s existing atomic read
transaction. It falls back to historical reconstruction when a branch has advanced.
Every manifest undergoes independent proof validation; shared inputs reuse only
a locally reconstructed proof. Source identity, all record/hash claims, ancestry,
operation uniqueness, interventions and final event/state hashes remain checked.
Tests verify extended branches preserve their original experiment boundary and
that corrupt prefix hashes are rejected on this fast path.

The intermediate calculation-only reuse did not meet the local maximum-history
budget; its raw profile is retained in intermediate.json rather than concealed. No memory/FPS claim is made.

## Acceptance boundary

Full-suite and maximum-history results belong to this PR's exact-head Actions
and review evidence. The optimization alone is not a claim that every Windows
machine now meets the90-second bound. No timeout/assertion has been increased,
removed or skipped. Diyan review is required before merging this engine-consumer
optimization; canonical engine semantics are untouched.

## Idle observer work

The idle WebSocket loop also rebuilt complete snapshots even when no command
revision changed. A regression reproduced six get_runtime calls in0.6seconds
with pings. The corrected path reads a small owned revision boundary from existing
command rows/creation receipts and rebuilds only on change. Initial/restored branch
revision, idempotent retry, wrong-owner concealment, subsequent delta delivery and
existing auth/revocation/observer tests are covered. Credentials are still checked
every cycle; the owner predicate remains in every metadata read. No schema or
WebSocket packet contract changes, global cache, polling delay increase or session
mutation was added. Further payload changes without a committed command revision
are outside the authoritative write contract; full snapshot reads still validate
initial and changed state.

A copied failed-test database was profiled directly before the current-boundary
fast path: total102.57seconds, including45.30seconds across ten independent branch
verifiers. This isolated the additional historical reconstruction bottleneck;
reducing only the calculation pass was insufficient. The profile used a copied
disposable test store, never a developer database. Subsequent acceptance evidence
is recorded in the PR.

## Common-prefix proof safety

_VerifiedPrefix is a private, per-verify_bundle object, never a wire field or a
global cache. It retains one reconstructed checkpoint state plus immutable
canonical prefix-record/ancestry strings and the already-checked operation IDs.
Its memory is bounded by one parent state and the existing operation limit, not
one state per operation. The first branch proves this prefix from resolved inputs.
A later branch must match every record (including command and state/event hashes),
resolved scenario and ancestor metadata. Differences take the full replay path.
Distinct suffixes always execute real copy-on-write transitions. Final state/event
hashes, interventions, trial inputs and the comparison digest are verified as
before. No browser/provider/claimed snapshot can inject a prefix proof.

Tests demonstrate a new proof is constructed on each bundle verification and
reject a changed later-branch state hash, event hash, command, duplicate operation ID, scenario or ancestry.
The earlier current-boundary fix reached the real large archive/download checks,
but its offline subprocess failed under the unchanged30-second budget. Its profile
is retained; the prefix-proof increment specifically addresses that remaining work.

## Final local acceptance

At source 743916c, the unchanged bounded-forkcast Playwright project passed: 1 test in 2.7 minutes, including the 90-second comparison arrival and 30-second offline verifier budgets. The same copied dense disposable database completed comparison in 30.06 seconds versus 102.57 seconds before the later optimizations. These are single local observations, not percentile guarantees. Raw dense profiles are retained alongside the smaller benchmark.

