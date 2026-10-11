# Independent client execution results — CAE v0.3.1

Executed 2026-10-11 using the built Windows EXEs and an isolated installed wheel.
The driver ran with Python `-I`, outside source import resolution, and asserted that
`cae.__file__` belonged to site-packages. Client applications import only the public
SDK; neither imports broker-service internals or retrieves provider credentials.

| Observation | Actual result |
|---|---|
| Broker process | CAE-Broker.exe, PID 5092 |
| Application A | CAE-Console-Client.exe, Python console application, PID 8328 |
| Application B | CAE-Desktop-Client.exe, independent Tk desktop, PID 13164 |
| Authenticated app identities | console-client and desktop-client, derived by broker enrollment |
| Simultaneous connections | Both reported broker PID 5092 after two completed cycles |
| Authorized operations | Status and provider diagnostics succeeded from both applications |
| Unauthorized operations | Both client shutdown attempts denied; export, identity override and forbidden model denied |
| Termination test | Application A process tree forcibly terminated |
| Continued desktop work | Application B advanced from cycle 2 to cycle 5, still broker PID 5092 |
| Credential availability | stored before and after Application A termination |
| Minimal live authentication | One models GET through broker: valid authentication, API available |
| Lifecycle | Clean stop, start, restart, forced broker crash, recovery and final clean stop passed |
| Credential changes | None; no production credential mutation calls |

The runtime driver result is retained locally at `.tmp/broker-validation-1/results.json`.
It contains fixed metadata, not provider keys or response bodies. This temporary run
directory is excluded from Git and distributions. Test process IDs are historical;
the validation broker was stopped at completion.

After the final client build, `scripts/test_broker_apps.ps1` repeated the full
installed-wheel/two-EXE/lifecycle/crash-recovery test successfully without `--live`.
This second run made no provider API request. Both runs ended with the broker stopped.

Both examples build as standalone executables. The console source is
`examples/broker_console.py`, desktop source `examples/broker_desktop.py`; source
execution uses the installed public SDK and requires explicit interpreter enrollment.
An interpreter is one identity for all its scripts. Do not use the test-only
`--verify-denial` option on an administrator-enrolled interpreter.

Install/start instructions and SDK examples are in [BROKER_PROTOCOL.md](BROKER_PROTOCOL.md).
Validation does not establish hostile same-account isolation, code signing or
independent Windows 11 acceptance. The production credential file was retained,
and no Codex authentication settings were accessed or modified.
