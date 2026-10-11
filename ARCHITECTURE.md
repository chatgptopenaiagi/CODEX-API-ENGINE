# CAE architecture

## Universal client development

`clients/` contains public Python, .NET, C++, Node.js and PowerShell SDKs. All use
the existing protocol v1 and kernel-authenticated named pipes; the broker is not
duplicated. Python composes the exported BrokerClient. C# and C++ implement native
client transport; PowerShell loads the .NET SDK and Node uses an in-process Node-API
binding to the C++ SDK. No helper process masks the calling application's identity.
External applications in `integration-lab/` import only these public interfaces.
See [client contracts and recovery](docs/CLIENT_SDKS.md).

## v0.3.1 independent broker

```mermaid
flowchart LR
    A[Console client process] --> SDK[BrokerClient / local named pipe]
    B[Desktop client process] --> SDK
    SDK --> IPC[CAE-Broker.exe: SID + executable enrollment]
    IPC --> Runtime[Existing AccessRuntime: policy / quota / audit]
    Runtime --> Vault[Windows Credential Manager]
    Runtime --> Providers[Existing seven provider adapters]
```

`pipe_transport.py` provides native overlapped I/O and kernel peer identity;
`ipc_protocol.py` validates framed JSON and explicit enrollment; `broker_client.py`
is the public client SDK; `broker_service.py` owns the runtime and eight connection
workers; `broker_control.py` supervises startup/shutdown without system installation.
`examples/broker_console.py` and `examples/broker_desktop.py` import only the public
SDK and build into separate application EXEs. The service does not import either UI.

No broker code relies on Codex CLI, Control Center, a calling application lifecycle,
environment API keys or changes to Windows authentication. The existing `CAE()`
composition remains backward compatible and explicitly in-process. This broker runs
under the current Windows account; separate service-account isolation is not implemented.
See [protocol](docs/BROKER_PROTOCOL.md) for trust boundaries and failure behavior.

## Previous architecture and compatibility

For the current CODEX ACCESS ENGINE v0.3.0 architecture, see
[Access Engine](docs/ACCESS_ENGINE.md) and [policy/audit design](docs/POLICY_AUDIT.md).
The v0.2.0 architecture below documents the retained compatibility interfaces.

Version 0.2.0 provides a synchronous SDK, native Windows credential backend,
in-process policy broker, bounded HTTPS connector, diagnostic snapshots, explicit
health monitoring, CLI and a separate human-operated test console.

```mermaid
flowchart TD
    Human[Human developer] --> Console[CAE CLI / Test Console]
    Console --> Manager[Credential Manager]
    Manager --> Store[Windows Credential Manager]
    App[Application] --> SDK[CAE SDK]
    SDK --> Broker[Policy broker]
    Broker --> Store
    Broker --> API[Fixed-origin HTTPS connector]
    API --> OpenAI[Official OpenAI API]
    Monitor[Health monitor] --> SDK
    SDK --> Diagnostics[Sanitized status snapshots]
```

Codex CLI is a development tool outside the runtime graph. Its login state is not
read or modified. CAE credentials belong to the current Windows account, using
`CAE/openai/<profile>` targets and `CRED_TYPE_GENERIC` with local-machine persistence
(user scoped, survives logoff, does not roam).

## Module ownership

| Module | Responsibility |
|---|---|
| `credential.py` | Store protocol, Win32 bindings, verified writes, lifecycle/import |
| `security.py` | Identifier/key syntax checks and recursive redaction |
| `api.py` | TLS, fixed origin/routes, bounded response reads, retry/error policy |
| `broker.py` | Immutable explicit grants, deny-before-read, bounded metadata audit |
| `engine.py` | Public SDK, schema validation, status and request composition |
| `monitor.py` | Opt-in polling with explicit lifecycle |
| `cli.py`, `gui.py` | Human administration and diagnostics |

All executable library code lives in `src/cae`. Root-level component directories
hold navigation/design notes; there are no duplicate Python package trees.

## Decisions

1. Use Win32 Credential Manager directly through typed `ctypes` declarations to
   avoid a configurable keyring backend silently selecting plaintext storage.
2. Use standard-library HTTPS with system certificate validation, a fixed origin,
   no redirects and no environment proxy support. This reduces configuration paths
   that could send an authorization header to an unintended endpoint.
3. Separate administrator lifecycle methods from the application SDK. Only trusted
   infrastructure code implements `CredentialStore.read`; consuming applications
   use broker operations and never receive a stored secret.
4. In-process grants are policy coordination, not authenticated process identity.
   The host composes grants. A separate Windows service identity and authenticated
   IPC require a later implementation and independent security review.
5. Probe with one model-list GET, no generation. Retry safe model-list operations
   at most three times after the initial attempt; never automatically replay POST.
6. Do not persist request bodies, responses, full exceptions or credential-derived
   diagnostics. Audit records contain only timestamp and fixed outcome.
7. Shipping artifacts are explicitly built from `src/cae` and a GUI launcher.
   No wildcard repository data inclusion is permitted.

## Concurrency and extension

The credential manager serializes lifecycle calls on a manager instance. Windows
performs each stored credential write; cross-process compare-and-swap lifecycle
transactions are not provided. Treat each profile as having one provisioning owner.
HTTP connections are created per call. Broker audit and engine health snapshots use
locks. Monitor start is idempotent; stop waits for the in-flight bounded call.

`CredentialStore` and `Transport` are trusted dependency-injection seams. Never
load their implementations from untrusted application-controlled configuration.
Future providers should use separate connector implementations and explicitly
scoped policies rather than making this connector's origin arbitrary.
