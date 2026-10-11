# Installation

For the current development build, run `scripts/setup.ps1` and `cae-control-center`.
After `scripts/release.ps1`, install `dist/0.3.0/codex_api_engine-0.3.0-py3-none-any.whl`
or launch `dist/0.3.0/CAE-Control-Center.exe`. Published v0.2.0 instructions follow.

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
