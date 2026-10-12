# Universal clients — executed validation

Date: 2026-10-11. Milestone snapshot: local commit `d969373`.
Local development only; nothing pushed or published. Later security development is
recorded separately in [0.5.0.dev1 validation](SECURITY-0.5.0-dev1.md).
Windows build 19045 x64, Python 3.14.7, .NET SDK 10.0.401, Node 26.8.1,
LLVM 22.1.8/MSVC 14.51, PowerShell 7.6.6, Electron 44.7.0.

## Results

| Check | Executed result |
|---|---|
| Original baseline | 153 tests, 92.37% statement coverage, Ruff/strict mypy passed |
| Updated Python suite | 160 tests passed; 92.53% aggregate coverage |
| New Python client facade | 7 tests; 100% statement coverage |
| Ruff and strict mypy | Passed, including new Python client |
| .NET SDK / app | Built with warnings treated as errors |
| C++ / Node-API | Built with `-Wall -Wextra -Werror` |
| Five-language acceptance | Passed with unchanged v0.3.1 broker binary |
| Electron plus five languages | Six applications passed against the same broker |
| Hostile-server acceptance | 60 passed cases across five languages |
| Credential/archive inspection | 67 files/archive members; zero credential matches |
| Historical v0.3.1 assets | Original hashes retained, including broker executable |
| Source Gitleaks | Passed; no detected credentials in Git-eligible files |
| Public CI/publication | Not run/published: this mission authorizes local development |

The six-application run used broker PID **18396**, then **24056** after a clean
restart. All applications returned their enrolled identities and the same PID,
listed mock models, inspected health/capabilities, rejected shutdown and spoofing,
and rejected generation without any provider POST. C++ was forcibly terminated;
the five surviving applications continued and then recovered after broker restart.
The broker remained active after client exit and shut down cleanly via the separately
enrolled administrative test executable. That executable is a lab tool, not a client
permission escalation endpoint. No production vault entries were read or changed.

Server-adversary cases: valid response, wrong server hash, wrong image, wrong request
ID, unsupported version, wrong broker PID, duplicate keys, array result, arbitrary
error text, oversized response frame, timeout, truncated frame. Wrong server tests
assert zero application request bytes were transmitted. This validates actual Windows
pipes and processes, not only mocks of transport. Provider HTTP itself is mocked.

## Commands and artifacts

```powershell
./scripts/test.ps1
./scripts/build_clients.ps1
./.venv/Scripts/python.exe scripts/validate_clients.py
./.venv/Scripts/python.exe scripts/validate_client_security.py
./scripts/setup_electron_lab.ps1
./.venv/Scripts/python.exe scripts/validate_clients.py --electron .tmp/electron-lab/node_modules/electron/dist/electron.exe
./.venv/Scripts/python.exe scripts/check_client_artifacts.py
./.venv/Scripts/python.exe scripts/audit_publication.py --gitleaks .tmp/gitleaks/gitleaks.exe
```

Broker used: `dist/0.3.1/CAE-Broker.exe`, unchanged SHA-256
`8f0bc7ff1949a803d0397629a4cadb0658c3db7195791c6c41ab24e74bd0c9ce`.

Development distributions in `dist/0.4.0-clients/`:

- `python/cae_client-0.4.0-py3-none-any.whl` and `cae_client-0.4.0.tar.gz`
- `dotnet/Cae.Client.0.4.0.nupkg` and `dotnet-client/Lab.Client.exe`
- `CAE-Cpp-Client.exe` and packaged C++ headers
- `nodejs/cae-client-0.4.0.tgz`, with the native module inside
- `powershell/CAE/CAE.psd1` and accompanying module/DLL
- `CROSS-LANGUAGE-RESULTS.json`, `CLIENT-SECURITY-RESULTS.json`,
  `ARTIFACT-VERIFICATION.json`, `SHA256SUMS.json`

Python and Node packages were installed into fresh repository-local test directories.
Python applications ran with `-I` using the installed wheel, not repository imports.
.NET/C++ applications run as their own executables. PowerShell loads the packaged DLL.
The Electron client uses the installed Node SDK from its trusted main process.

The first harness run failed on a missing required profile in its synthetic policy;
the fixture was corrected. Electron initially failed loading the native module;
the Windows delay-load hook and explicit installed-package discovery fixed it.
Assertions were retained. Electron's downloader initially used its default cache;
the one task-created archive was verified, moved into the repository cache, and the
default-cache copy removed. The setup script now explicitly sets the supported cache
variable. No pre-existing cache files or global configuration were changed.

## Preservation and remaining limitations

The operator's existing broker remained ready at PID 10268, version 0.3.1. Its
configuration, production Windows credentials, protected input file and published
tags were not modified. `apy_key.txt` remains Git-ignored. Artifact inspection reads
it only in memory to detect accidental inclusion; no value or derived hash is reported.

This completes the defined five-language v0.4 client acceptance milestone, not the
full v1.0 platform. The engine package retains 0.3.1; client packages are 0.4.0.
Executables are unsigned. Tests ran on Windows 10 build 19045, not Windows 11.
The existing pipe transport's Python statement coverage remains below the later 95%
security-module target; no C++/.NET statement coverage percentage is claimed.
Same-user hostile-code isolation, loaded-code attestation, live application revocation,
stronger service identity, centralized admin UI, routing, installer and soak acceptance
remain later milestones. No provider generation was paid for during validation.

No service responded on literal loopback ports 11434, 1234 or 8000 during the local
provider check. This is not proof that no model exists elsewhere, but it cannot
establish the required working local-provider acceptance. Cloud authentication was
not re-run unnecessarily. Windows 11 and real local-model acceptance remain external
validation prerequisites for any v1.0 claim.

Implementation references: [Windows peer PID](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getnamedpipeserverprocessid),
[Node-API](https://nodejs.org/api/n-api.html),
[Electron Windows native-module loading](https://www.electronjs.org/docs/latest/tutorial/using-native-node-modules).
