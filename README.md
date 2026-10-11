# CODEX ACCESS ENGINE (CAE)

Current source: **0.5.0.dev2**, a development audit-correlation increment.
The published foundation remains **v0.3.1**. This is not a v1.0 release.

Broker-local audit request IDs now link authentication, policy and result metadata;
legacy audit records remain readable. Audit storage failures return fixed errors.
M1 remains partial: bounded disk retention and crash-safe rotation are unfinished.
See [M1 validation](docs/validation/AUDIT-M1.md) and
[continuation instructions](docs/continuity/NEXT_SESSION.md).

## Application administration and limits

The development broker adds authenticated operator commands: `cae apps list`,
`register`, `inspect`, `authorize`, and `revoke`, each with an explicit
`--broker-config` path. Registration grants no provider permissions. Policy updates
take effect after restart; enrollment revocation takes effect on the next connection
to the development broker. The older v0.3.1 broker requires a restart for revocation.

Policies can limit daily requests, requests per UTC minute, and concurrent provider
requests. Limits are checked before credential access and provider communication.
See [application administration](docs/APPLICATION_REGISTRY.md) and
[executed security validation](docs/validation/SECURITY-0.5.0-dev1.md).

Development engine artifacts are in `dist/0.5.0.dev2/`; client SDKs are in
`dist/0.4.0-clients/`. Full local validation requires building both before running
`scripts/test.ps1`. Historical release artifacts are not overwritten.

## Universal clients: 0.4.0 development

Python, C#/.NET, C++, Node.js and PowerShell clients now connect to the existing
independent broker through protocol v1. Client packages are versioned 0.4.0;
the original client acceptance used the preserved 0.3.1 broker and also passes against
0.5.0.dev1. No new release is published.
See [SDK installation and examples](docs/CLIENT_SDKS.md) and
[executed cross-language validation](docs/validation/CLIENTS-0.4.0.md).

Build with `scripts/build_clients.ps1`; test with `scripts/validate_clients.py`
and `scripts/validate_client_security.py`. New artifacts are isolated in
`dist/0.4.0-clients/`. Existing broker, credentials and historical releases are retained.

CAE is a capability-based AI connectivity, protected credential and policy platform.
It is **not an AI agent**. Windows x64 and Python 3.14 are the supported build platform.
The repository and distribution names remain `CODEX-API-ENGINE` and `codex-api-engine`
for compatibility. v0.3.1 is the initial independent Windows broker release.
Windows build 19045 was validated locally; Windows 11 is a target, not a certification.
All current executables are unsigned. The v0.2.0 release remains available unchanged.

## Download v0.3.1

Get the [official release](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/tag/v0.3.1).
The seven release assets are:

| Artifact | Download |
|---|---|
| Independent broker | [CAE-Broker.exe](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/download/v0.3.1/CAE-Broker.exe) |
| Console application | [CAE-Console-Client.exe](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/download/v0.3.1/CAE-Console-Client.exe) |
| Desktop application | [CAE-Desktop-Client.exe](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/download/v0.3.1/CAE-Desktop-Client.exe) |
| Human administration UI | [CAE-Control-Center.exe](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/download/v0.3.1/CAE-Control-Center.exe) |
| Python SDK | [Python wheel](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/download/v0.3.1/codex_api_engine-0.3.1-py3-none-any.whl) |
| Python source distribution | [Source archive](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/download/v0.3.1/codex_api_engine-0.3.1.tar.gz) |
| SHA-256 manifest | [SHA256SUMS.json](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/download/v0.3.1/SHA256SUMS.json) |

Install the SDK with Python 3.14:

```powershell
python -m pip install https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/download/v0.3.1/codex_api_engine-0.3.1-py3-none-any.whl
```

For the following enrollment commands, clone or download the tagged repository and
place the downloaded assets in its `dist/0.3.1/` directory. Compare each software
file's `Get-FileHash -Algorithm SHA256` value with the manifest before launching it.
The existing binaries are used directly; rebuilding is optional. The source
distribution contains the Python package; the repository provides the complete
tests, enrollment utility and build scripts.

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

Run the two client commands in separate terminals, or launch the desktop EXE directly
with its connection argument. Launch `CAE-Control-Center.exe` for human credential and
provider administration; it retains its trusted in-process mode and is not the broker.
Keep the broker running independently of either client.

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

### Connecting an application

```python
import json
from pathlib import Path
from cae import BrokerClient

client = BrokerClient(**json.loads(Path(".cae/broker/client.json").read_text()))
print(client.get_status())
print(client.diagnostics())  # Offline; no generation or provider key returned
```

Enroll an application's exact executable path and SHA-256 in `broker.json`, assign its
application label appropriate rules in `runtime.toml`, then restart the broker.
The client cannot choose that label. Enrolling a Python interpreter authorizes every
script it runs; use separate frozen executables when applications need distinct rules.

### Providers and credentials

Enrollment creates an OpenAI/default read-only configuration. Existing CAE credentials
are reused without replacement. For a new installation only, `cae add` provisions a
key through a hidden prompt. No key belongs in the JSON/TOML files or command line.
Edit the administrator-owned `.cae/broker/runtime.toml` to configure provider names,
kinds, profiles and policy grants, using [provider configuration](docs/PROVIDERS.md)
and [examples/access.toml](examples/access.toml). Restart after configuration changes.
Cloud endpoints are restricted; local provider endpoints must use literal loopback
addresses. Applications cannot modify provider configuration through IPC.

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

See [broker validation](docs/BROKER_VALIDATION.md), [Access Engine guide](docs/ACCESS_ENGINE.md), [provider contracts](docs/PROVIDERS.md),
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
For current development, use `pip install .` or the wheel in `dist/0.5.0.dev1/` after building.

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

The default console grant permits read-only models, health, diagnostics and usage. See
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
