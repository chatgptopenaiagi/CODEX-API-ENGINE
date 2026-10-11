# CODEX API ENGINE (CAE) 0.2.0

CAE is a reusable OpenAI authentication, credential management and connection engine.
It is **not an AI agent**. Windows 11 x64 and Python 3.14 are the primary platform.

## Features

- Windows Credential Manager integration and credential profiles
- OpenAI API connectivity, diagnostics and connection testing
- Python SDK with an in-process authorization broker
- Windows graphical test console
- Python wheel, Windows executable and source distributions

## Official release

Download the existing v0.2.0 artifacts from
[GitHub Releases](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases).
The release includes `SHA256SUMS.json`; compare downloaded file hashes before use.

Install the published wheel with Python 3.14:

```powershell
python -m pip install https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/download/v0.2.0/codex_api_engine-0.2.0-py3-none-any.whl
```

For the standalone console, download `CAE-Test-Console.exe` from the same release
and launch it on Windows. It bundles Python and Tk and does not require a separate
Python installation. The executable is unsigned.

The application SDK never returns credentials. Windows Credential Manager protects
stored keys for the current Windows account. A default-deny, in-process broker
checks explicit application/profile/operation grants before accessing a key.

## Install

From the source repository in PowerShell:

```powershell
./scripts/setup.ps1
./.venv/Scripts/cae.exe add
./.venv/Scripts/cae.exe test
./.venv/Scripts/cae-console.exe
```

`add` uses a hidden terminal prompt. The console GUI masks and clears the key entry.
Do not pass secrets on command lines. `cae import <path>` imports an existing UTF-8
key file without deleting it. Keep such files outside version control.

The package is distributed through GitHub Releases; no PyPI publication is claimed.
For local development, install the wheel in `dist/` or use `pip install .`.

## Application SDK

```python
from cae import CAE

engine = CAE()
print(engine.get_status())
print(engine.test_connection())
```

Additional SDK operations:

```python
engine.configure()       # Inspects configuration; does not create credentials
models = engine.list_models()
status = engine.get_status()  # JSON-compatible metadata; no network request
```

The default console grant permits model listing only. See
[SDK usage](docs/SDK.md) for trusted-host composition and Responses API access.
No environment-key fallback, custom API host, proxy forwarding, credential export,
or Codex login integration is enabled.

## Build and verify

```powershell
./scripts/test.ps1
./scripts/build.ps1
./scripts/build.ps1 -Executable
./scripts/release.ps1
```

Wheel/source packaging uses an explicit package allowlist and checks archives for
forbidden files. Executable builds include only the GUI launcher and its imports.
The release script never uploads, tags, signs or publishes anything.

## Documentation

- [Architecture](ARCHITECTURE.md) and [security model](SECURITY.md)
- [SDK](docs/SDK.md), [broker](docs/BROKER.md), [credential administration](docs/CREDENTIALS.md)
- [Diagnostics and monitoring](docs/DIAGNOSTICS.md)
- [Installation](docs/INSTALLATION.md), [Windows builds](docs/PACKAGING.md)
- [Troubleshooting and FAQ](docs/TROUBLESHOOTING.md), [versioning](docs/VERSIONING.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md), [roadmap](ROADMAP.md), [contributing](CONTRIBUTING.md)
- [Local validation evidence and platform limits](docs/VALIDATION.md)

## Security boundary

The Windows account is the storage boundary. Other programs running as that same
account may use Windows credential APIs. Python in-process grants coordinate trusted
applications; they cannot isolate hostile code in the same interpreter or Windows
account. No IPC listener is installed. See the roadmap for a separate-identity broker.

API authentication, billing, and permissions are independent of ChatGPT subscriptions
and Codex CLI login. CAE never reads or writes Codex authentication state.
Never commit API keys or other real credentials. Key files, private key containers,
environment files, virtual environments and release binaries are excluded from Git.
