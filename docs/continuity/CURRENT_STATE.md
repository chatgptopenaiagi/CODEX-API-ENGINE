# Current state

CODEX ACCESS ENGINE (CAE), repository/package names CODEX-API-ENGINE /
codex-api-engine. Snapshot: 2026-10-11, branch `feat/security-registry`, implementation
HEAD `b379795d109dbdfa62b079805d8db9aef3368457`, version **0.5.0.dev1**.
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
| Audit | PARTIALLY IMPLEMENTED: schema-constrained JSONL, bounded in-memory history; disk rotation and request correlation NOT IMPLEMENTED |
| Control Center | IMPLEMENTED: existing trusted in-process administration GUI; independent registry management GUI NOT IMPLEMENTED |
| Routing / installation | Capability-selection routing and Windows installer/uninstaller NOT IMPLEMENTED |

The broker owns policy, vault and provider communication. Client protocol v1 returns
results, never provider keys. `CAE()` remains the compatible trusted in-process SDK;
`BrokerClient` and the language SDKs reach the independent broker. Control Center
and Codex are not broker runtime dependencies. Same-account process separation is
not an OS boundary against hostile code running as that account.

Local `dist/0.5.0.dev1/` contains CAE-Broker.exe, CAE-Control-Center.exe,
CAE-Console-Client.exe, CAE-Desktop-Client.exe, the engine wheel/source distribution
and SHA256SUMS.json. `dist/0.4.0-clients/` contains C++ executable, .NET package/app,
Node package/native binding, PowerShell module and Python client wheel/source.
These are ignored local development outputs, **not remote downloadable releases**.
Python >=3.14 and Windows x64 are required; native SDK/build prerequisites are in
[ENVIRONMENT_STATE](ENVIRONMENT_STATE.md). No artifact was rebuilt for this mission.
