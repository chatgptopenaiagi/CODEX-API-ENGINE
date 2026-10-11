# Security increment — 0.5.0.dev1

Local validation on 2026-10-11, Windows build 19045 x64 / Python 3.14.7.
This is unpublished development, not a completed v0.5 or v1.0 release.

## Implemented and executed

- Operator-only `apps list/register/inspect/authorize/revoke`, authenticated through
  the existing executable enrollment; no client administration endpoint.
- Persistent registration metadata, default-deny registration, revoked-ID tombstones,
  serialized edits and DACL-preserving replacement with tested failure recovery.
- Per-request enrollment revalidation. Source-process and **frozen executable** tests
  admitted the native C++ client, revoked it, observed `access_denied` on its next
  request, and confirmed the broker PID did not change.
- Authenticated status prevents the CLI from claiming immediate revocation on v0.3.1;
  it reports that restart is required instead.
- Atomic daily/minute quotas and per-rule concurrent provider slots. Persistence,
  exception cleanup and denial before vault/provider access tested.
- Strict Python response typing and native peer-lookup failure cleanup.

`scripts/test.ps1`: **218 passed**, **95.24% overall statement coverage**, Ruff passed,
strict mypy passed (25 engine modules plus Python client). Coverage gates passed:
overall >=90%, and **each of 16 runtime trust-boundary modules >=95%**. These cover
access, API, audit, broker/client/supervisor, configuration, credentials, engine,
protocol, transport, policy, providers, registry and security. Native C++/.NET coverage
percentages and independent security review are not inferred from Python coverage.

Full validation requires native artifacts:

```powershell
./scripts/build.ps1 -Executable
./scripts/build_clients.ps1
./scripts/test.ps1
```

Pure Python tests remain selectable through pytest. CI now builds test artifacts
before the full gate and needs no production credentials. It has not been pushed or
run remotely during this local development mission.

## Packaged process acceptance

```powershell
./.venv/Scripts/python.exe scripts/validate_clients.py --broker-directory dist/0.5.0.dev1 --results-directory dist/0.5.0.dev1 --electron .tmp/electron-lab/node_modules/electron/dist/electron.exe
./.venv/Scripts/python.exe scripts/validate_client_security.py --integration-report dist/0.5.0.dev1/CROSS-LANGUAGE-RESULTS.json
./scripts/test_broker_apps.ps1
./.venv/Scripts/python.exe scripts/checksums.py
./.venv/Scripts/python.exe scripts/check_release.py --directory dist/0.5.0.dev1
```

All passed. Python, C#, C++, Node.js, PowerShell and Electron used broker PID **11536**,
then **7608** after restart. Authorized mock model access worked; administration,
spoofing and unauthorized generation were denied. The mock provider received no
denied-generation POSTs. Surviving clients continued after C++ termination and
recovered after restart. No provider secret was returned. Python and Node packages
were installed in isolated environments, not imported from repository source.

The hostile-server harness passed **60 cases** across five languages. The original
console/desktop lifecycle harness also passed, including crash recovery. All four
development executables passed smoke checks. The original v0.3.1 cross-language
evidence remains separately preserved under the 0.4 client artifact directory.

An additional installed-wheel CLI check ran all five registry commands against
isolated test configuration, including authorization with minute/concurrency limits
and persisted revocation. See [documented flags](../APPLICATION_REGISTRY.md).

## Artifacts and preservation

Files under `dist/0.5.0.dev1/`:

- `CAE-Broker.exe`, `CAE-Control-Center.exe`
- `CAE-Console-Client.exe`, `CAE-Desktop-Client.exe`
- `codex_api_engine-0.5.0.dev1-py3-none-any.whl`
- `codex_api_engine-0.5.0.dev1.tar.gz`
- `SHA256SUMS.json` and integration/security result JSON

The verifier checks package version, archive integrity, hashes and source/runtime
consistency. Credential scans passed. The original v0.3.1 artifacts retain their
hashes; v0.2.0 artifacts and tags were not modified. No tag, push or release was created.

The original operator broker remains ready at PID **10268**, version 0.3.1. Its
configuration and production Windows credentials were not changed. `apy_key.txt`
remains untouched and Git-ignored; artifact checks compare it only in memory.

Final environment hygiene found that the first .NET invocation had appended its
repository-local tool directory to persistent user PATH. That exact task-created
entry was removed and all other entries preserved. The build script sets
`DOTNET_ADD_GLOBAL_TOOLS_TO_PATH=false` and keeps .NET/NuGet caches in the repository.

## Remaining work and limits

The larger v1.0 mission remains incomplete. Remaining implementation includes audit
correlation/enrichment and bounded rotation, capability routing, central admin GUI,
installer/uninstaller, cancellation, upgrade recovery and soak validation. Same-user
hostile-code isolation, loaded-code attestation, signing and independent review are
not claimed.

Policy edits require restart; revocation cannot undo an accepted request. Minute
limits use fixed UTC windows and trust the system clock. Concurrency is per runtime.
The 0.4 native clients map unfamiliar limit errors to a fixed generic error.

No local model was validated: default loopback ports 11434/1234/8000 did not respond.
Provider behavior was explicitly mocked. No unnecessary cloud generation request was
made. This Windows 10 host cannot establish Windows 11 acceptance. A v1.0 or
production-ready label would be premature.
