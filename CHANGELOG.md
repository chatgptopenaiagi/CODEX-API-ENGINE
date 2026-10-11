# Changelog

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
