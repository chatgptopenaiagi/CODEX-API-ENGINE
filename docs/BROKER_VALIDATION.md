# CAE v0.3.1 broker validation

Executed locally on 2026-10-11, Python 3.14.7, Windows x64 build 19045. This is a
Windows 10 execution record; the Windows 11 target has not been separately certified.
No remote source push, tag modification or GitHub release was performed.

## Baseline and implementation

Before changes, `scripts/test.ps1` confirmed the reported v0.3.0 baseline: 118 passing
tests, 92.43% statement coverage, Ruff and strict mypy passing. Existing providers,
SDK compatibility, Control Center and production credential namespaces were retained.
The new separate process uses named pipes and centralized existing AccessRuntime.
Build version 0.3.1 keeps all new artifacts apart from both historical versions.

## Executed checks

```powershell
./scripts/test.ps1
./scripts/build.ps1 -Executable
./.venv/Scripts/python.exe scripts/checksums.py
./.venv/Scripts/python.exe scripts/check_release.py
./scripts/test_broker_apps.ps1
./.venv/Scripts/python.exe scripts/audit_publication.py --gitleaks .tmp/gitleaks/gitleaks.exe
./.tmp/broker-wheel/Scripts/python.exe -m pip install --no-index --no-deps dist/0.3.1/codex_api_engine-0.3.1-py3-none-any.whl
./.tmp/broker-wheel/Scripts/python.exe -I scripts/validate_broker_apps.py --artifacts dist/0.3.1 --work .tmp/broker-validation-1 --live
```

The regression run passed **153 tests**, with **92.37% runtime statement coverage**.
Ruff passed and strict mypy passed across 24 runtime modules. Coverage includes native
pipe calls; the standalone EXE subprocess integration is an additional executed test,
not folded into that coverage percentage. No assertion was relaxed to mask a failure.
An outdated version assertion was updated to 0.3.1. A DACL test was corrected to inspect
binary ACE SIDs because Windows renders the current RID-500 SID as the SDDL alias LA.

Security and IPC tests executed:

- OS SID/path/hash enrollment mismatches denied; client application-name spoofing rejected.
- Unauthorized export, credential/provider modification and administrative stop denied.
- Forbidden model, provider and profile requests denied before synthetic key reads.
- Actual pipe DACL: protected, exactly the current user SID and SYSTEM; no other trustees.
- Malformed JSON, duplicate keys, non-finite values, incorrect schema/types and unknown fields rejected.
- Oversized length prefix rejected; incomplete request times out; bad server pin refused.
- Forty repeated connections with six concurrent callers succeeded; all eight slots can
  be exhausted, extra connects time out, and capacity recovers after clients disconnect.
- First-instance exclusivity, separate Python broker process start/stop/restart and crash
  recovery passed. Native handles release on process exit; no stale PID file is trusted.
- Synthetic provider credential echoes redacted from responses and audit; existing API,
  quota, Windows vault roundtrip and legacy SDK security tests remain passing.
- A real trickling loopback HTTP response was interrupted by its configured body deadline.

The executable integration passed both clients on the same broker PID, continued desktop
operation after forced console termination, denied application administrative access,
clean shutdown, restart, forced broker crash and subsequent recovery. See
[integration results](INTEGRATION_RESULTS.md) for recorded process IDs and installed SDK evidence.
One minimal authenticated OpenAI model-list GET succeeded through the broker. No live
generation/embedding requests and no new provider credentials were used.

## Artifacts and reproducible validation

Artifacts are in `dist/0.3.1/`: CAE-Broker.exe, CAE-Control-Center.exe,
CAE-Console-Client.exe, CAE-Desktop-Client.exe, codex_api_engine-0.3.1-py3-none-any.whl,
codex_api_engine-0.3.1.tar.gz and SHA256SUMS.json. All four EXEs ran `--self-test`.
Use `scripts/test_broker_apps.ps1` for the installed-wheel/executable integration without
a live API request. CI is configured to run it after builds, but these workflow changes
have not been pushed or remotely executed.

`scripts/check_artifacts.py --directory dist/0.3.1` passed, including forbidden-file
checks and comparison against the retained key in memory without displaying it.
`scripts/checksums.py` and `scripts/check_release.py` passed SHA-256 integrity and
packaged-runtime/source matching for the wheel, source archive and all four EXEs.
Gitleaks scans of 105 Git-eligible files, existing Git history and the distribution
directory returned no findings. `git diff --check` passed. The original four v0.2.0
release asset hashes still match the preexisting publication manifest; v0.3.0 artifacts
were not rebuilt or modified. `apy_key.txt` remains Git-ignored and unchanged.

## Remaining limits

No separate service-account identity, hostile same-account isolation, code signing,
SCM service installation, cross-user live penetration test or Windows 11 acceptance is
claimed. DACL and SID-denial behavior are checked without creating another Windows
account. Enrolled interpreters authorize all their scripts. Hashes attest on-disk files,
not loaded process integrity. The fixed worker limit mitigates ordinary exhaustion but
cannot prevent same-account denial of service. Cloud adapters beyond OpenAI retain
mock-contract validation. OS DNS resolution can exceed socket-level timing guarantees.
See [protocol](BROKER_PROTOCOL.md) and [security model](../SECURITY.md).
