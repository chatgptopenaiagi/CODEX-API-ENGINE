# Roadmap

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
