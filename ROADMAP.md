# Roadmap

## 0.5.0.dev4 — M2 development acceptance

Versioned chat/embedding registry, opt-in authorization-aware deterministic routing,
local/cloud restrictions, conservative fallback, bounded responses and additive
protocol operations are implemented. Current acceptance is recorded in
[ROUTING-M2](docs/validation/ROUTING-M2.md). M3 real local-model validation remains
separate and must not be inferred from mock-provider tests.

## 0.5.0.dev3 — M1 complete within documented contract

Bounded managed retention, rotation and process-crash recovery are implemented.
Final acceptance is recorded in [the M1 storage report](docs/validation/AUDIT-M1-RETENTION-ROTATION.md).
M2 capability routing remains the next planned milestone; no M2 implementation is
part of this mission. The older roadmap entries below describe historical states.

## 0.5.0.dev2 — M1 partial

- [x] Request correlation, validated metadata, legacy audit compatibility and tests
- [x] Fixed audit-failure responses and process-exit shutdown confirmation
- [ ] Bounded audit retention, safe rotation and crash/disk/concurrent-writer acceptance

Complete M1 before M2 routing. See [current continuation](docs/continuity/NEXT_SESSION.md).

## 0.5.0.dev1 — security increment (unpublished)

- [x] Authenticated administrative application registry and persistent enrollment metadata
- [x] Next-connection revocation in the development broker; old-broker restart warning
- [x] Daily/minute quotas, concurrency limits and model/provider policy restrictions
- [x] Configuration failure recovery, native identity failures and strict response validation
- [x] 90% overall / 95% critical-module Python coverage gates
- [x] Frozen broker, legacy clients and six-application compatibility acceptance
- [ ] Complete v0.5 audit enrichment/retention and independent security review

The source uses a development version deliberately. v0.6 routing and real local-model
acceptance, v0.7 central administration UI, v0.8 installer/uninstaller, v0.9 soak and
recovery hardening, and v1.0 Windows 11/release acceptance remain unfinished.

## v0.4.0 — universal clients (locally validated)

- [x] Python compatibility facade, C#/.NET, C++, Node.js and PowerShell SDKs
- [x] Six real applications including Electron on one unchanged broker
- [x] Authenticated access, policy denial, no credential disclosure, crash/restart recovery
- [x] 60 hostile-server cases; isolated client distributions and checksums
- [x] Preserve original broker, interfaces and historical release artifacts
- [ ] Authorized public publication and Windows 11 acceptance

See [measured validation](docs/validation/CLIENTS-0.4.0.md). Client packages use 0.4.0;
the preserved broker/runtime package remains 0.3.1. Next: persistent administrative
application registry, revocation and policy resource limits (v0.5). Routing/local-model
acceptance (v0.6), administrative UI (v0.7), installation (v0.8), long-running reliability
(v0.9) and Windows 11/stable distribution acceptance (v1.0) remain unfinished.

## v0.3.1 — independent Windows broker (local development)

- [x] Separate CAE-Broker.exe with local named pipes and explicit DACL
- [x] OS peer SID/image checks, executable enrollment and client-side server pinning
- [x] Central policy, vault access, provider routing and audit
- [x] Bounded concurrent connections, lifecycle CLI and crash recovery validation
- [x] Two independent client EXEs; one survives termination of the other
- [x] Installed-wheel integration and executable smoke tests
- [ ] Separate least-privilege Windows service identity and installer-managed ACLs
- [ ] Signing, independent penetration review and Windows 11 acceptance

The completed IPC work below is superseded by v0.3.1; separate-identity isolation
remains pending. No new provider or unrelated feature is introduced.

## v0.3.0 — CODEX ACCESS ENGINE development

- [x] Seven provider adapters and secret-free capability sessions
- [x] Human-readable model/operation policy with deny precedence
- [x] Atomic UTC-day quota ledger with restart persistence
- [x] Durable metadata audit, health/latency and observed usage
- [x] Control Center and extended CLI
- [x] ARX/CGC evidence/continuity interfaces
- [x] Isolated build artifacts and manual tag release workflow
- [ ] Separate service identity and authenticated IPC
- [ ] Live certification of all providers; signed Windows 11 acceptance build

The earlier phase list below records the v0.2 foundation and longer-term direction.

## v0.2.0 — Phases 1 and 2 foundation

- [x] Windows Credential Manager and lifecycle administration
- [x] Typed, installable application SDK and separated human console
- [x] Fixed-origin OpenAI connector, model listing and explicit Responses calls
- [x] Explicit in-process broker grants and application profiles
- [x] Structured diagnostic snapshots and opt-in monitoring
- [x] Synthetic unit/security tests, Windows storage integration and build checks
- [x] Wheel, source and Windows executable tooling; CI workflow

## Phase 3 — security boundary beyond a trusted host

- Windows service running under a separate least-privilege identity
- Named pipes with restrictive DACLs, peer-token verification and remote-client denial
- Durable administrator-owned policies, authenticated app enrollment and revocation
- Per-app rate limits, quotas, concurrency controls and delegated scopes
- Durable redacted audit sinks and independent threat-model/penetration review
- Provider-side rotation workflows with transactional replacement and rollback
- Signed installers, SBOM, pinned build inputs and artifact attestations

## Phase 4 — provider abstraction

- Explicit provider contracts for authentication, requests and health semantics
- Azure OpenAI, Anthropic, Google and local provider adapters
- Provider-specific credential isolation and policy scopes
- Compatibility suites with no implicit credential or endpoint reuse

## Evolution proposals

Stabilize status schema and error codes before expanding transport support. Add async
and streaming APIs only with cancellation, backpressure and redaction design reviews.
Do not add remote broker access until authenticated transport and key isolation exist.
