# Requirements traceability (re-verified 2026-10-24)

The full row-level matrix (source, frontend, backend, persistence, tests, runtime
evidence, severity, next action) is [FINAL_REQUIREMENTS_AUDIT.md](FINAL_REQUIREMENTS_AUDIT.md).
This file is the current-state overlay: it does not duplicate those rows, it records what
changed since that snapshot and where each capability lives **right now**.

Source of requirements: the [official rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md)
(re-read 2026-10-24) and the repository epic/issues summarised in the audit.

## Counts (35 decomposed requirements, from the audit matrix)

| Result | Count |
|---|---:|
| verified | 24 |
| partial | 4 |
| blocked (external decision/credential) | 6 |
| missing (optional) | 1 |

By category (verified/total): challenge 5/6, frontend 5/5, backend 2/2, persistence 5/5,
security 2/3, agents 2/3, ux 1/2, submission 2/6, optional 0/3. These are counts over a
decomposition chosen by the audit author, not an official score. Critical gaps are all
non-code: public judge access (D4), final video (D3), rights sign-off (S3), hosted-model
evidence (C6/A3) and the final submission (D6).

## Status of capabilities by location

| Capability | State |
|---|---|
| Replay, Fan Lens, ProofTrail, Control Room, ForkCast, Data Hub, Studio, 3D observer | In `main`; automated tests pass (backend 547, browser 141 on the #106 head) |
| Fan Lens 1 Hz sampling, fixed Event Wire viewport, replay-stability tests (#104); One Moment · Three Stories, route-health sweep (#105); axe WCAG scan, highlight manifest/player/renderer, submission packet (#106) | **Merged**: `main` = `92d05ed`, post-merge CI green |
| Hosted Foundry / Agent Framework execution | Blocked: no credential or cost authorization; offline deterministic path only |
| Public judge access, demo video, rights approval, submission | Not done; see audit rows D3/D4/S3/D6 |

## Corrections to earlier claims

- "One Moment/Three Stories already exists" was **wrong** in the 2026-10-22 audit; the
  feature is new in PR #105.
- F1 (passive replay stability) was marked verified, but Fan Lens was still fetching on
  every 200 ms tick (61 requests / 12 s) until PR #104.
- U2 remains **partial**: LCP, long tasks, heap and a synthetic interaction latency now have
  one-machine measurements, but field INP and React Profiler counts are unmeasured (see
  [PERFORMANCE_AUDIT.md](PERFORMANCE_AUDIT.md)).

## Not independently re-verified this session

Maximum-history ForkCast latency, Azure/provider behaviour, physical-GPU (Iris Xe /
RTX) results, and every sub-bullet of the original GitHub issues. Prior evidence for
those stands only as dated in their own documents.
