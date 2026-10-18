# Local application security correction — 2026-10-18

This is a focused correction discovered during PR #31 review, independent of asset licensing. It does not certify a public Azure deployment or replace issue #23.

## Confirmed dependency finding

PyPA pip-audit 2.10.1 reported 12 advisory entries (including duplicate database entries) in resolved Starlette 0.52.1 and pytest 9.0.2. Windows StaticFiles UNC resolution is relevant to our Windows-served `/assets` route: [upstream high-severity advisory](https://github.com/Kludex/starlette/security/advisories/GHSA-wqp7-x3pw-xc5r). No outbound SMB attack was attempted.

FastAPI 0.128.4 constrained Starlette below the patched major version. This justified updating FastAPI to 0.143.3 and explicitly pinning patched Starlette 1.3.1; pytest's patch is 9.0.3. Other direct versions remain unchanged. [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/) and actual PyPI metadata were inspected before selecting compatible releases. The change must pass the full backend and real browser suite; registry advisory scans do not prove an absence of all vulnerabilities.

Other reported Starlette findings concern reconstructed URL confusion, urlencoded form limits and unconstrained HTTPEndpoint method dispatch. This app has JSON endpoints and explicit FastAPI methods, not form parsers or unconstrained HTTPEndpoint subclasses. The package upgrade removes those reported versions without pretending every advisory was directly exploitable here.

## Defense in depth

- `LocalStaticFiles` rejects UNC, drive-qualified and backslash paths **before** filesystem resolution. Normal inherited containment/symlink checks remain. Tests replace realpath with a forbidden sentinel, avoiding external connections.
- A raw ASGI request boundary rejects backslashes, nonabsolute URL paths, duplicate Host fields and URL-delimiter characters in Host before framework URL reconstruction. It does not introduce host-based authorization or a deployment-domain allowlist.
- POST/PUT/PATCH bodies are bounded at 2,000,000 actual received bytes, including chunked requests and misleading/missing Content-Length. Requests exceeding the limit return 413 before JSON parsing. Exactly-at-limit behavior is covered with a small test budget. Invalid JSON remains 422; valid seed generation remains 200.
- Existing CORS is limited to the two local Vite origins. It is not authentication. Hosted inference still requires explicit configuration and its admin token; no billable calls were made.

Six focused regression cases cover unsafe Windows paths, valid local assets, malformed Host, JSON/bounds behavior and raw chunked/malformed-target handling. Wider replay/API/browser regressions are required before merge. A preliminary pytest command run from the repository root failed collection because `app` is imported from the backend working directory; the correct documented backend command was then used. No tests or assertions were disabled.

## Remaining release boundaries

Mutable imported-match ingestion is a local synthetic-data operation, not an authorized shared operator-session API. Internet deployment still needs Vishwam's separate session/rate-limit/operational review. No engine, user accounts or cloud resources were added. Optional Foundry dependency sets and the entire global Python environment are outside this asset-focused requirements scan; the hosted path remains disabled.
