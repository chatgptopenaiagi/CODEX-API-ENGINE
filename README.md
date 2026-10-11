# CODEX ACCESS ENGINE (CAE) 0.3.1

CAE is a capability-based AI connectivity, protected credential and policy platform.
It is **not an AI agent**. Windows 11 x64 and Python 3.14 are the primary platform.
The repository and distribution names remain `CODEX-API-ENGINE` and `codex-api-engine`
for compatibility. v0.3.1 is a local development build; the public release remains v0.2.0.

## Independent Windows broker

`CAE-Broker.exe` is a separate process with local Windows named pipes, an explicit
account-scoped DACL, OS peer-process verification, executable SHA-256 enrollment,
centralized policy/credential access, eight concurrent connections and bounded IPC.
Clients cannot select their application identity or retrieve provider keys.

```powershell
python -m pip install .\dist\0.3.1\codex_api_engine-0.3.1-py3-none-any.whl
python scripts/enroll_broker.py --artifacts dist/0.3.1 --directory .cae/broker
cae broker start --config .cae/broker/broker.json
cae broker status --config .cae/broker/broker.json
cae broker health --config .cae/broker/broker.json
cae broker diagnostics --config .cae/broker/broker.json
.\dist\0.3.1\CAE-Console-Client.exe --connection .cae/broker/client.json
.\dist\0.3.1\CAE-Desktop-Client.exe --connection .cae/broker/client.json
cae broker restart --config .cae/broker/broker.json
cae broker stop --config .cae/broker/broker.json
```

Enrollment authorizes the two exact client executables and the enrollment command's
underlying Python interpreter as administrator. **All code run by that interpreter
has the same administrative identity**; it is not script isolation. Run enrollment
with the same Python installation used by `cae`. Protect configuration/build files.
Rebuilt executables must be explicitly re-enrolled. Never enroll untrusted images.

For external applications, use the installed `BrokerClient` SDK and the supplied
non-secret `client.json` connection descriptor. See [protocol and SDK examples](docs/BROKER_PROTOCOL.md),
[broker validation](docs/BROKER_VALIDATION.md), and [two-client results](docs/INTEGRATION_RESULTS.md).
The existing `CAE()` SDK and Control Center remain available as trusted in-process
interfaces; they do not silently switch to IPC. Same-account hostile programs remain
outside the security boundary. This is not a separate-identity Windows service.

## Access Engine SDK

```python
from pathlib import Path
from cae import CAE

engine = CAE(config=Path("examples/access.toml"))
print(engine.health())       # Offline snapshot, not a network probe
print(engine.diagnostics())
print(engine.providers())
print(engine.connect())      # Explicit single model-list request
print(engine.models())
engine.close()
```

Apps receive broker-bound provider sessions through `engine.provider(name)`.
Sessions support `list_models()`, `chat()`, `embeddings()`, `health()`,
`diagnostics()` and `usage()`. Policies control provider, profile, operation, model
and daily request limits. Credentials never enter an application's SDK calls.

Built-in adapters: OpenAI, Azure OpenAI, Anthropic, Gemini, Ollama, vLLM and
LM Studio. Unsupported capabilities are explicit; Anthropic embeddings are not
implemented. Adapter contracts are tested with mocks; new cloud providers have
not been live-certified.

Use `cae-control-center` for human oversight or `cae --config examples/access.toml diagnostics`
for machine-readable, offline Codex/application inspection. Diagnostic results are
observations, not proof of identity or authority.

See [validation evidence](docs/VALIDATION_0.3.md), [Access Engine guide](docs/ACCESS_ENGINE.md), [provider contracts](docs/PROVIDERS.md),
[policy and audit design](docs/POLICY_AUDIT.md), and [migration](docs/MIGRATION_0.3.md).

## Features

- Windows Credential Manager integration and provider-isolated credential profiles
- Seven cloud/local provider adapters, diagnostics and connection testing
- Python SDK, model-scoped policy, atomic daily quotas and metadata audit
- Windows Control Center for credentials, providers, health, audit and policy
- Python wheel, Windows executable and source distributions

## Existing published v0.2.0 release

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
./.venv/Scripts/cae-control-center.exe
```

`add` uses a hidden terminal prompt. The console GUI masks and clears the key entry.
Do not pass secrets on command lines. `cae import <path>` imports an existing UTF-8
key file without deleting it. Keep such files outside version control.

The package is distributed through GitHub Releases; no PyPI publication is claimed.
For v0.3.1 development, use `pip install .` or the wheel in `dist/0.3.1/` after building.

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
forbidden files. Executable builds include explicit broker/UI/client entry points and imports.
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
account. The independent IPC listener is explicitly started by the operator; no
Windows service is installed. A separate-identity service remains roadmap work.

API authentication, billing, and permissions are independent of ChatGPT subscriptions
and Codex CLI login. CAE never reads or writes Codex authentication state.
Never commit API keys or other real credentials. Key files, private key containers,
environment files, virtual environments and release binaries are excluded from Git.
