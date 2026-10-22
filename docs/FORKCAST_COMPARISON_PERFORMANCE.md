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
checks remain. Engine/RNG/models/manifest-verifier files and analytical formulas
are unchanged.

The new regression first failed against original main with the explicit
post-audit fourth-replay assertion. It passes on the candidate, as do58 focused
runtime/reproduction tests. Both independent committed example verifiers pass.

## Versioned source fingerprint

The experiment implementation hash intentionally includes experiments.py. Its
fingerprint changes when this file changes; the core engine fingerprint does not.
The committed ForkCast example updates **only** this experiment-source fingerprint.
Its events, operations, core fingerprints, state/event hashes, inputs and comparison
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

| Measurement | Original main | Candidate ca72516 |
|---|---:|---:|
| Total replayed command transitions per comparison | 120 | 90 |
| Independent verifier transitions | 30 | 30 |
| Measured median ms (3 samples only) | 5950.82 | 5263.84 |
| Comparison hash | c071ffb03edad0d6dedc86dcff76f1f0cebd3fce5ace4c5054b4fce5236e075d | identical |

[Raw baseline](benchmarks/forkcast-reuse/before.json) and
[raw candidate](benchmarks/forkcast-reuse/after.json) preserve every observation.
The repeatable result is25% fewer replay transitions with independent-verifier
work unchanged. The observed11.5% median reduction is a small, high-variance local
sample, not a P95/production improvement guarantee. No memory/FPS claim is made.

## Acceptance boundary

Full-suite and maximum-history results belong to this PR's exact-head Actions
and review evidence. The optimization alone is not a claim that every Windows
machine now meets the90-second bound. No timeout/assertion has been increased,
removed or skipped. Diyan review is required before merging this engine-consumer
optimization; canonical engine semantics are untouched.
