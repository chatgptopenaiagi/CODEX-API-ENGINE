# Continuity mission validation

## 0.5.0.dev3 M1 retention evidence

Final run: 299 tests, 95.64%, Ruff/strict mypy and 17 module gates passed.
Six real applications, 60 hostile-server cases, frozen legacy clients and artifact
integrity passed. Baseline rerun: 247 tests, 95.36%, 16 module gates. Current final
commands/counts and native/package/security evidence are in
[the retention report](../validation/AUDIT-M1-RETENTION-ROTATION.md). Temporary detailed
logs use `.tmp/retention-*.log`; raw machine-local reports are not published.

## Latest development evidence — 0.5.0.dev2

See [M1 validation](../validation/AUDIT-M1.md): **247 passed**, **95.36% coverage**,
Ruff and strict mypy passed; all 16 critical-module gates passed. Six actual clients
passed against the updated broker, followed by 60 hostile-server cases. Package,
runtime-source and executable self-tests passed. Providers are mocked. The report
records the failed CI shutdown assertion and local report-sharing race, their fixes
and retests. Retention/rotation and real local/cloud inference remain unvalidated.

## Preserved checkpoint evidence

Executed 2026-10-11 on Windows 10 build 19045 x64 against implementation
`b379795d109dbdfa62b079805d8db9aef3368457`; no feature changes or artifact rebuilds.

| Command/check | Actual result |
|---|---|
| `./scripts/test.ps1` | 218 passed in 35.93s; 95.24% aggregate statement coverage; Ruff and strict mypy passed |
| `scripts/check_coverage.py` (included above) | Overall >=90%; each of 16 selected critical modules >=95% |
| `scripts/check_release.py --directory dist/0.5.0.dev1` | Existing artifact integrity, metadata, checksums and runtime/source consistency passed |
| `scripts/check_artifacts.py --directory dist/0.5.0.dev1` | Protected-key and archive exclusion verification passed; no key printed |
| `scripts/audit_publication.py --gitleaks .tmp/gitleaks/gitleaks.exe` | 149 Git-eligible files scanned at initial inspection, no findings; includes unrelated untracked files but they are not staged |
| Gitleaks Git history, redacted | Exit 0, no findings |
| Packaged cross-language harness | Six applications / five languages passed, broker PID 25140 then 19888 after restart |
| Hostile-server harness | 60 cases passed across five languages |
| Checkpoint source scan | 160 Git-eligible files, no Gitleaks findings; 12 intended staged paths reviewed |
| Continuity documents / resume | All ten documents present; relative links resolve; PowerShell resume script executed successfully |
| Historical remote preservation | Exact before/after remote tag refs and full release/asset metadata unchanged |

The packaged run includes Electron, installed Python wheel and installed Node
package, authorized mock model access, denied administration/spoofing/generation,
survival after C++ termination and client recovery after broker restart. Mock provider
responses do not establish real local/cloud inference. Existing frozen-broker
revocation tests are included in the 218-test suite.

Reproduce from the repository root after prerequisites/artifacts exist:

```powershell
./scripts/test.ps1
./.venv/Scripts/python.exe scripts/check_release.py --directory dist/0.5.0.dev1
./.venv/Scripts/python.exe scripts/check_artifacts.py --directory dist/0.5.0.dev1
./.venv/Scripts/python.exe scripts/validate_clients.py --broker-directory dist/0.5.0.dev1 --results-directory .tmp/continuity-validation --electron .tmp/electron-lab/node_modules/electron/dist/electron.exe
./.venv/Scripts/python.exe scripts/validate_client_security.py --integration-report .tmp/continuity-validation/CROSS-LANGUAGE-RESULTS.json
```

Electron setup is explicit and optional for the five-language run; see recovery
instructions. The complete six-application claim requires the Electron argument.
Local raw logs: `.tmp/continuity-tests.log`, `continuity-clients.log`,
`continuity-hostile.log`, `continuity-history.json`; JSON reports under
`.tmp/continuity-validation/`. They are ignored, not needed to recover source.
Committed historical evidence is linked in COMPLETED_MILESTONES.md; this report
records current measured outcomes. No raw private enrollment/configuration is copied.

No production credential mutation or operator-broker lifecycle command was issued.
The preexisting v0.3.1 operator broker remained running. Protected input is ignored
and untracked. Secret scanning detects known patterns; it is not a proof against
every possible undiscovered secret. CI and remote recovery are recorded separately
in GITHUB_STATE.md and RECOVERY_PROCEDURE.md.
