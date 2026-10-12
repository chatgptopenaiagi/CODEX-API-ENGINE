# Download CAE for Windows

CAE lets enrolled applications request authorized AI capabilities through an
independent local broker. Provider credentials remain broker-owned.

The public foundation is [v0.3.1](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/tag/v0.3.1).
New M4 builds are development candidates, not yet published or installation-ready.
Do not confuse a source checkpoint with a downloadable release.

For a future validated M4 prerelease, the recommended download will be a portable
ZIP containing the Control Center, broker, clients, instructions, license notices
and checksums. No installer is currently validated. Standalone EXEs bundle Python;
the Python wheel is for developers with Python 3.14 or newer.

Only Windows 10 x64 build 19045 has local acceptance evidence. Windows 11 is a
target, NOT_RUN. Executables are unsigned; no verified-publisher claim is made.

Verify the SHA-256 of each download using `Get-FileHash -Algorithm SHA256`, comparing
with the exact release manifest. Extract into a new directory; never overwrite an
older installation. Double-click Control Center. Follow [quickstart](QUICKSTART_WINDOWS.md).

Local model use needs an independently installed compatible inference server.
CAE does not download models or start Qwen. Cloud providers need separately
configured credentials and affirmative policy; no cloud inference is automatic.

Portable removal: close only your portable Control Center and explicitly stop only
your test broker, then remove only your own extracted package. Keep private broker
configuration, enrollment, policies, audits and Windows credentials. No uninstaller
or automatic user-data deletion exists. Do not delete an existing installation to
resolve a problem. See [troubleshooting](TROUBLESHOOTING_WINDOWS.md).
