# Current CAE development state

Version **0.5.0.dev5**, branch `feat/security-registry`. Checkpoint SHA:
`git log -1 --format=%H -- docs/continuity`; verify actual HEAD/remote before work.
Runtime build source: bf6107f; exact-model fix: 9b31d14. Published stable foundation
remains v0.3.1; v0.2.0 is preserved. M1/M2 are complete within their contracts.
**M3 local packaged acceptance PASS; final remote checkpoint verification pending.**
[Packaged M3 evidence](../validation/LOCAL-INFERENCE-M3-PACKAGED.md).

| Component | Current evidence |
|---|---|
| Broker | Independent Windows Named Pipe EXE, OS peer identity, exact enrollment, eight workers |
| Policy/registry | Default deny, exact provider/model allowlists, next-connection revocation, durable day/minute quotas, concurrency limits |
| Audit | Correlation plus managed JSONL rotation/retention, crash recovery, legacy compatibility |
| Routing | Versioned chat/embedding contracts, authorized local/cloud selection, no post-dispatch replay |
| Clients | Python/C#/C++/Node/PowerShell/Electron, six actual mock-provider clients passed against dev5 |
| Real local inference | PASS: dev5 console EXE to dev5 broker EXE to approved llama.cpp Qwen, one bounded LOCAL_ONLY call |
| Recovery | PASS: disposable compatible endpoint refusal/termination/reset/timeout/malformed reply/restart; isolated broker restart |
| Providers | Seven adapters preserved; llama.cpp reuses existing vLLM-compatible wire implementation |
| Vault | Windows Credential Manager architecture preserved; production credentials not used in M3 |
| GUI/install | Existing Control Center preserved; centralized registry GUI and installer remain unfinished |

Artifacts: `dist/0.5.0.dev5/` (four EXEs, wheel, sdist, checksums). Historical dev4
outputs lack the fix and remain untouched. Client contracts remain 0.4.0; local
lab packages `.tmp/m2-clients` are unchanged. No new downloadable GitHub Release.
Final local gates: 414 tests, 95.95%, 18 critical gates, Ruff/strict mypy, six mock
clients, 60 hostile cases, independent wheel and legacy executable acceptance.
Windows 10 build 19045 tested; Windows 11, signing and long soak remain unverified.
Real Qwen restart/outage NOT_RUN. No POK adapter, moderation, trusted roles,
cancellation or hostile same-user isolation claim. M4 follows final M3 preservation.
