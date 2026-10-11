# Installation

For v0.3.1, download the seven assets from the
[official release](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/tag/v0.3.1).
Install `codex_api_engine-0.3.1-py3-none-any.whl` with Python 3.14. For independent
broker enrollment/startup, follow the [README](../README.md#independent-windows-broker)
and [protocol guide](BROKER_PROTOCOL.md). Standalone EXEs bundle their Python runtime.
Source development uses `scripts/setup.ps1`; no rebuild is necessary to use the
published executables. All EXEs are unsigned. Windows build 19045 was tested;
Windows 11 remains the target without a certification claim.

The following v0.2.0 instructions describe retained legacy interfaces.

Requirements: Windows 11 x64, Python 3.14 with Tcl/Tk, and network access to
`api.openai.com:443`. Administrator privileges are not required for credential storage.
Run CAE as the Windows account that will own the API key.

Source development: `./scripts/setup.ps1` creates `.venv` and installs development
tools. Wheel installation: `python -m pip install dist/codex_api_engine-0.2.0-py3-none-any.whl`.
The wheel has no runtime third-party dependencies. Native storage fails closed on
non-Windows systems; the pure-Python wheel tag does not imply a cross-platform vault.

Launch `cae-console` after installation or `dist/CAE-Test-Console.exe` after building.
Use Add to enter a key through the masked field, then Test connection. To replace a
key, select the same profile and use Replace. Removal affects only that profile.

The standalone executable bundles Python and Tk. It is unsigned and may trigger
Windows reputation prompts; review the source and artifact hashes before deployment.
No installer, Windows service, startup entry or firewall rule is installed.

ChatGPT subscriptions and Codex login do not supply an OpenAI API credential. CAE
only accesses its own Windows credential targets and never changes Codex state.
