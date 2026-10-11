# Changelog

## 0.5.0.dev3 — managed audit retention

- Opt-in validated audit limits, private store ownership and bounded Windows locks.
- Persisted rotation/deletion intents, partial-tail recovery and fail-closed errors.
- Archive-aware audit reads and additive non-secret storage diagnostics.
- Required audit before credential-presence diagnostics; registry retains audit configuration.
- Isolated Windows concurrency/process-exit/failure tests and benchmark.
- Cross-language restart harness rejects fresh files containing stale broker identity.
- Separate development artifacts; historical releases/configurations preserved.

## 0.5.0.dev2 — partial M1 audit increment

- Broker-generated request correlation shared by nested runtime events; allowlisted
  decision/status/error metadata and monotonic elapsed time; legacy JSONL compatible.
- Fixed audit-unavailable response when broker audit recording fails.
- Supervisor waits for authenticated broker process exit rather than mistaking a
  transient pipe failure for completed shutdown (observed prior CI failure).
- POK source-based compatibility analysis; no external application changes.
- Disk retention/rotation remain unfinished. No stable release or main merge.

## 0.5.0.dev1 — unpublished security development

- Operator-only application list/register/inspect/authorize/revoke commands.
- Persistent registration metadata, Windows-locked edits, DACL-preserving replacement
  and fail-closed enrollment reload on each new broker connection.
- Persistent per-minute quotas and provider concurrency limits; policy edits retain
  quota identity, and old rules keep their previous behavior by default.
- Strict Python response field typing and additional native failure/recovery tests.
- Separate development packages; no production credential migration or public release.

## 0.4.0 client SDKs — local development

- Python facade, native C# and C++ clients, asynchronous Node-API SDK and PowerShell module.
- Explicit descriptor discovery, mutual Windows peer checks, protocol v1 responses,
  capability discovery, bounded I/O and fresh-connection recovery without request replay.
- Independent cross-language applications, hostile-server acceptance tests and isolated packages.
- Existing engine/broker 0.3.1 binary and published releases retained; no new public release.

## 0.3.1 — local development, 2026-10-11

- Independent Windows named-pipe broker with kernel-derived peer identity, executable
  enrollment, server pinning, explicit DACL, remote rejection and concurrent clients.
- Public BrokerClient SDK; lifecycle CLI start/stop/restart/status/health/diagnostics.
- Standalone Python console and Windows desktop clients using only the public SDK.
- Centralized existing policy/quota/audit/vault/provider routing, bounded framed IPC,
  provider body deadlines and sanitized failures. No credential IPC endpoints.
- Security, process lifecycle, crash recovery, two-client and installed-wheel validation.
- Separate dist/0.3.1 artifacts, preserving v0.3.0 builds and the v0.2.0 public release.
- No separate Windows service identity or hostile same-account isolation is claimed.

## 0.3.0 — local development

- Platform name: CODEX ACCESS ENGINE; package/repository names remain compatible.
- Seven cloud/local provider adapters and secret-free capability sessions.
- Explicit TOML policy, model allowlists, deny precedence and atomic persistent quotas.
- Metadata audit, provider health/latency and observed usage.
- Extended CLI and CAE Control Center; ARX/CGC evidence/continuity contracts.
- Version-isolated builds and manual release pipeline, preserving v0.2.0 artifacts.
- Default status schema 2; explicitly injected legacy Broker retains v0.2 behavior.

## 0.2.0 — 2026-10-11

Initial repository foundation:

- Native Windows Credential Manager with verified imports, replacement and removal.
- Secret-free application SDK and explicit in-process authorization grants.
- Official OpenAI HTTPS connection probe, models and Responses support.
- Sanitized error boundaries, bounded retry/read policies and metadata audit.
- JSON health snapshots, explicit polling monitor, CLI and masked test console.
- Tests, documentation, CI and local wheel/source/executable release tooling.

Limitations: trusted-host policy only, no IPC service; unsigned Windows executable;
no provider-side key issuance/revocation; no published package registry release.
