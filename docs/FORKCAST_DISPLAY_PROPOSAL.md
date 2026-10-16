# ForkCast display preparation (#8)

Status: **prepared and tested with development fixtures; real experiments remain blocked by #6/#7/#9**. This branch adds no production route, experiment runner, simulation clock, branch persistence or fake API. The display component is not imported by the application. A separate Vite test harness labels every example as DEVELOPMENT FIXTURE ONLY; no branch was run.

## Proposed comparison boundary

Audit hardening: the validator accepts unknown input and rejects malformed nested shapes without throwing. It checks explicit metric/status enums, nonblank checkpoint and branch provenance, exact trial/hash key sets, duplicate evidence and single-trial range consistency. Development fixtures cannot claim `verified_rule_based`. Display limits are nine supported metrics, 20 paired trials and 10,000 evidence references per metric; these are proposed UI safety limits, not authorization or engine quotas. A backend auditor is still required to verify actual events, hashes and calculations.

`ProposedExperimentComparison` is explicitly versioned `comparison/proposal-1`, pending agreement with Diyan and Mahir. It is a display DTO, not a replacement experiment manifest. It carries match/scenario/experiment IDs, one immutable parent checkpoint reference/hash, distinct branch IDs, engine version, an opaque manifest reference, common comparison window/cutoff, paired trial IDs/seeds/output hashes, descriptive metric means/ranges/differences and branch/trial/time-scoped evidence references.

The internal consistency check rejects incompatible schemas, missing provenance, repeated branches/trials/metrics, mismatched trial counts/hashes, nonfinite or contradictory summaries, incorrect mean differences, unit mismatch and evidence outside the selected branch/trial/window. It cannot establish that an event exists or that a mean was calculated from the engine. The authoritative backend verifier must do that before returning a publishable result. Frontend types/checks do not confer authorization or factual verification.

Null/unavailable and measured zero are distinct. Means/ranges are descriptive and include paired sample count; no confidence interval, statistical significance or calibrated real-world probability is invented. A positive delta is neutral information, not automatically an improvement (for example, more turnovers may be undesirable). Tactic summaries and hashes must come from the real server adapter when available.

## Prepared UI

`ForkCastComparison` provides two branch cards, a responsive metric table, deltas, range/sample information, keyboard-accessible provenance/event details and visible limitations. Loading, empty, error, invalid, zero and unavailable states are covered. It has no run/fork/publish buttons. The test harness exercises these states; development data remains visibly labeled even if the component is accidentally mounted elsewhere.

## Isolated preview and tests

```powershell
# frontend directory
npm run test:contracts
# Optional manual development preview
npm run dev -- --port 8766 --strictPort
# Open http://127.0.0.1:8766/contract-tests/preview.html
```

The contract suite performs its own strict TypeScript check and uses a separate Vite server; normal production builds use only index.html and exclude the harness/fixture data. Four tests cover contradiction/provenance rejection, keyboard evidence access, all UI states and mobile overflow. This is display testing, not branch reproducibility testing. CI runs this suite after the existing real-API browser suite.

## Team handoff and remaining gates

- **Diyan:** agree names/units and IDs against #2/#9; provide a real bounded runner over isolated #6 checkpoints and #7 interventions, with paired seed derivation, ancestry, revision/cancellation semantics, hashes and manifest. Never translate legacy fixture generation into a fake branch run.
- **Satvik:** replace the proposal adapter only after those contracts are implemented; connect real progress/cancel/retry, manifest download and evidence navigation. Maintain parent immutability and one authoritative clock. Complete #6 continuation tests first.
- **Mahir:** use branch/trial/time-scoped source references plus approved calculation values for #16, tools and broadcast. An inference model cannot replace these calculations. The display's verification_status must be forwarded from the deterministic auditor, not assigned by the frontend.
- **Vishwam:** the prototype adds no runtime dependency or deployment endpoint. It adds a strict contract/browser CI command using the existing Vite/Playwright packages. Before release, test session isolation, resource quotas, cancellation and the actual checkpoint→intervene→fork→compare journey with real services.

Required future engine tests: identical branch settings/hash parity, intervention effects only after effective tick, parent hash unchanged, no cross-branch state/event contamination, paired-seed reproducibility, recalculated metrics, interrupted/cancelled/concurrent trials, unavailable metrics, empty intervals, corrupted manifests and replay cutoff enforcement. These are not marked passed by the development fixture tests.
