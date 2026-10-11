# Changelog

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
