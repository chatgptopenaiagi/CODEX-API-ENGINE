# Verified milestone history

## 0.5.0.dev4 M2 — COMPLETE within documented contract

Implementation `ee1947e7c467ee8de46e9acee7ba0e2176c51688`; 393 tests, 95.92%,
18 critical gates, package integrity and independent remote recovery passed.
Versioned capability registry, explicit routing grants, local/cloud selection and
conservative no-replay execution are implemented. Six actual applications passed
new routed mock requests and legacy operations; 60 hostile-server cases passed.
Final milestone status is authoritative in [ROUTING-M2](../validation/ROUTING-M2.md).
Engine artifacts: `dist/0.5.0.dev4/`; current lab builds: `.tmp/m2-clients/`.
Existing client SDK contracts remain 0.4.0; no release was created.

## 0.5.0.dev3 M1 — COMPLETE within documented contract

The retention/rotation implementation supplements, rather than replaces, the
correlation work below. See [final acceptance](../validation/AUDIT-M1-RETENTION-ROTATION.md)
for current counts and limits. Resolve implementation SHA with
`git log -1 --format=%H -- src/cae/audit_storage.py`; artifacts: `dist/0.5.0.dev3/`.
Earlier entries below retain historical partial-milestone evidence.

## Historical 0.5.0.dev2 increment (then partial)

0.5.0.dev2 implements audit request correlation and fixed audit-failure responses,
plus process-exit confirmation and lab-report sharing-error recovery. **247 tests,
95.36% coverage, six real clients and 60 hostile-server cases passed**. See
[M1 results, including corrected failures](../validation/AUDIT-M1.md).
Artifacts: `dist/0.5.0.dev2/`; original client SDKs remain version 0.4.0.
Resolve the implementation revision with `git log -1 --format=%H -- src/cae`.
Bounded retention/rotation remain unfinished; this is not completion of M1 or v0.5.

## Preserved earlier milestones

| Milestone | Commit and evidence | Scope / limitation |
|---|---|---|
| v0.2.0 | `a62f33baef7e05412ebc959182b385803790fa2a`, published tag/release v0.2.0 | Original API, vault, in-process SDK and console foundation |
| v0.3.1 | `8b8bf3d4ece60a6448921381cb1755abd9b46e1e`, published tag/release v0.3.1; [baseline](../validation/CURRENT-BASELINE.md) | Independent named-pipe broker and two external clients; historical 153 tests / 92.37% |
| v0.4.0 client increment | `d9693738342d30b76e018a16b91bc778c59bbbc2`; [client validation](../validation/CLIENTS-0.4.0.md) | Six applications, five SDK languages, 60 hostile-server cases; historical 160 tests / 92.53%; locally built, no v0.4 release |
| v0.5.0.dev1 security increment | `327bd2fe23accf76fe3f1a63c4103d48b3201bcf`; [security validation](../validation/SECURITY-0.5.0-dev1.md) | Registry, hot revocation, quota/concurrency limits; 218 tests / 95.24%, not completion of all v0.5 work |
| Environment cleanup record | `b379795d109dbdfa62b079805d8db9aef3368457` | Exact task-created persistent PATH entry removed; future .NET startup prevention documented |

The continuity mission reran 218 tests, Ruff, strict mypy, critical-module coverage,
six-client packaged acceptance and all 60 hostile-server cases. See
[current evidence](VALIDATION_EVIDENCE.md); historical reports retain their original
publication-at-the-time statements and are not assertions about today's remote state.

Original artifacts: root `dist/` (v0.2.0), `dist/0.3.1/`; new artifacts:
`dist/0.4.0-clients/` and `dist/0.5.0.dev1/`. SDK package details and install examples
are in [CLIENT_SDKS](../CLIENT_SDKS.md). Historical release downloads remain on GitHub.
Native coverage, same-user isolation, signing, Windows 11 certification and real
local inference are not implied by these milestones.
