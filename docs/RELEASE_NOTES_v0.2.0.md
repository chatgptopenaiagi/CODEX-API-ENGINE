# CODEX API ENGINE (CAE) v0.2.0

First public release of CODEX API ENGINE, a reusable OpenAI API connectivity and
credential management engine for software developers. CAE is not an AI agent.

Includes:

- Reusable Python SDK for Python 3.14
- Windows Credential Manager storage, profiles and credential lifecycle administration
- OpenAI connectivity, model listing and explicitly authorized Responses requests
- Connection diagnostics and opt-in health monitoring
- In-process credential authorization broker with explicit operation grants
- Windows graphical test console and command-line administration
- Python wheel, Windows executable and source distribution

## Downloads

| Asset | Purpose |
|---|---|
| `CAE-Test-Console.exe` | Standalone Windows graphical console |
| `codex_api_engine-0.2.0-py3-none-any.whl` | Installable Python SDK |
| `codex_api_engine-0.2.0.tar.gz` | Python source distribution |
| `SHA256SUMS.json` | SHA-256 checksums for the three software assets |

These are the existing tested local artifacts, preserved without rebuilding for
publication. The release commit adds repository presentation and publication tooling;
runtime source and authentication architecture are unchanged.

## Installation

Download the wheel, verify its checksum, then run:

```powershell
python -m pip install ./codex_api_engine-0.2.0-py3-none-any.whl
```

Alternatively, launch the standalone executable. Provision credentials through the
masked console or hidden CLI prompt; never place API keys in source control.
OpenAI API authentication is independent of Codex CLI authentication and ChatGPT subscriptions.

## Security boundary and limitations

The broker is **in-process** and coordinates trusted applications. It does not
provide strong OS-level application isolation or authenticated interprocess identity.
Windows Credential Manager protects storage within the current Windows account;
other programs under that account may access its credentials through Windows APIs.

Windows 11 x64 is the primary target. Local validation ran on Windows build 19045
with Python 3.14.7; a Windows 11 acceptance run remains pending. The executable is
unsigned. No service, remote broker, enterprise isolation, provider-side key rotation
or PyPI publication is claimed. No real API key is required for standard CI.

See the repository's SECURITY.md, ARCHITECTURE.md and docs/VALIDATION.md for details.
