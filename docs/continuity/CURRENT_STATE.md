# Current state

## Current M2 development increment

Version **0.5.0.dev4**, branch `feat/security-registry`, starting checkpoint
`ac55a2fc29ed3d6e3b55e9afea7eea1e7f1440a1`. Routing is implemented and mock-tested;
final gates/synchronization are recorded in [ROUTING-M2](../validation/ROUTING-M2.md).
Resolve current implementation with `git log -1 --format=%H -- src/cae/routing.py`.
No real local/cloud inference, POK adapter, installer or stable release is claimed.
The older M1 synchronization evidence below remains historical.

Verified implementation: `9768e4aa40f1242895c4bfa320703375b8716a63`. Local M1 acceptance and
fresh remote recovery passed. Later checkpoint-only commits do not change runtime
artifacts. Current PR #2 remains a development draft; query live CI separately.


CODEX ACCESS ENGINE (CAE), repository/package names CODEX-API-ENGINE /
codex-api-engine. Snapshot: 2026-10-12, branch `feat/security-registry`, implementation
starting checkpoint `02153a7c5a8374c4e438fd7fd43e96c8778d9d03`, version **0.5.0.dev4**.
Resolve current implementation with `git log -1 --format=%H -- src/cae`.
Published stable foundation: **v0.3.1**. Resolve the latest checkpoint commit as
described in [NEXT_SESSION](NEXT_SESSION.md); verify live GitHub state separately.

| Component | Evidence category and state |
|---|---|
| Independent broker | IMPLEMENTED / TESTED: Windows local named pipes, explicit DACL, OS peer identity, enrollment, bounded connections, independent lifecycle |
| Clients | IMPLEMENTED / TESTED: Python, C#, C++, Node.js, PowerShell; Electron uses Node SDK. Six actual processes, shared broker PID, denial and restart recovery |
| Vault | IMPLEMENTED / TESTED: Windows Credential Manager abstraction and profiles; synthetic destructive tests only |
| Policy / registry | IMPLEMENTED / TESTED: default deny, explicit deny precedence, provider/model restrictions, operator registration/authorization/revocation, persistent day/minute quotas and per-rule concurrency |
| Providers | IMPLEMENTED / MOCK-TESTED: OpenAI, Azure OpenAI, Anthropic, Gemini, Ollama, vLLM, LM Studio; actual capabilities differ, inspect providers.py |
| Cloud/local validation | Historical OpenAI authentication is documented; no new live call here. Real local-model inference NOT VALIDATED |
| Audit | IMPLEMENTED / TESTED: request correlation plus opt-in bounded managed JSONL, Windows locks, rotation/recovery and legacy reads; see current acceptance report |
| Control Center | IMPLEMENTED: existing trusted in-process administration GUI; independent registry management GUI NOT IMPLEMENTED |
| Routing | IMPLEMENTED / MOCK-TESTED: versioned chat/embedding contracts, explicit/local-only/local-first/cloud-only selection, opt-in cloud/fallback; see M2 report |
| Installation | Windows installer/uninstaller NOT IMPLEMENTED |

The broker owns policy, vault and provider communication. Client protocol v1 returns
results, never provider keys. `CAE()` remains the compatible trusted in-process SDK;
`BrokerClient` and the language SDKs reach the independent broker. Control Center
and Codex are not broker runtime dependencies. Same-account process separation is
not an OS boundary against hostile code running as that account.

Local `dist/0.5.0.dev4/` contains CAE-Broker.exe, CAE-Control-Center.exe,
CAE-Console-Client.exe, CAE-Desktop-Client.exe, the engine wheel/source distribution
and SHA256SUMS.json. `dist/0.4.0-clients/` contains C++ executable, .NET package/app,
Node package/native binding, PowerShell module and Python client wheel/source.
These are ignored local development outputs, **not remote downloadable releases**.
Python >=3.14 and Windows x64 are required; native SDK/build prerequisites are in
[ENVIRONMENT_STATE](ENVIRONMENT_STATE.md). New version-specific artifacts were built for changed source; prior versions remain intact.

Current audit acceptance: [M1 storage report](../validation/AUDIT-M1-RETENTION-ROTATION.md).
Legacy audit files remain unchanged/unbounded until an operator explicitly enables
a new managed store. Development binaries are local only, not GitHub release assets.
