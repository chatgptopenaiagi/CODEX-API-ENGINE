# M2 capability routing validation

Status: **LOCAL ACCEPTANCE PASS — remote checkpoint/recovery pending**.
Development version: **0.5.0.dev4**. Branch: `feat/security-registry`.
Starting checkpoint: `ac55a2fc29ed3d6e3b55e9afea7eea1e7f1440a1`.
Implementation/final checkpoint revisions are resolved with Git; the final recovery
record will identify the concrete implementation SHA after it exists.

## Implementation and boundaries

[CAPABILITY_ROUTING](../CAPABILITY_ROUTING.md) is the normative threat model,
request/response schema, selection order, configuration and failure contract.
`routing.py` extends existing AccessRuntime; policy.py/provider config add opt-in
fields; broker_service.py/BrokerClient add operations without changing wire v1.
Registry updates preserve routing grants, existing quota IDs, models and provider
configuration. audit.py adds validated metadata without replacing M1 storage.
Provider normalization rejects mismatched returned model/incomplete status and no
longer treats partial token metadata as confirmation. All seven adapters remain.

Supported: chat_generation and embeddings (Anthropic chat only). Explicit-provider,
local-only, local-first and cloud-only selection; exact configured models; affirmative
cloud permission; pre-dispatch cloud fallback only when both request and policy allow.
No replacement after any adapter execution attempt. Default-deny, revocation,
per-provider quotas/concurrency and vault ownership remain in existing components.
No aggregate monetary budget, moderation, trusted role hierarchy, streaming or
provider cancellation is implemented. Legacy explicit-provider grants remain valid;
routing opt-in does not retroactively remove those permissions.

M1 baseline rerun: **299 passed in 59.95 s, 95.64%**, Ruff/strict mypy and all 17
original critical-module coverage gates passed. First M2 regression: **376 passed
in 61.60 s, 95.85%**, all 18 critical gates passed, routing initially 100%.
A later versioned run exposed the CLI test's old literal version expectation; the
assertion was updated to 0.5.0.dev4 and all seven CLI tests passed. The focused routing
suite now passes **94 tests**. No security assertion or coverage threshold was lowered.

## Environment and execution

Actual host: Windows 10 x64 build 19045; Python 3.14.7, PowerShell 7.6.6. Reused
existing .NET 10.0.401 SDK/.NET 8 target, Node 26.8.1, clang 22.1.8 and Electron
44.7.0 lab runtime. No global installs/PATH edits or production configuration changes.
Tests use synthetic providers/credentials and isolated named pipes/state.

```powershell
./scripts/resume-development.ps1
./scripts/test.ps1
./scripts/build_clients.ps1 -OutputDirectory .tmp/m2-clients
./scripts/build.ps1 -Executable
./.venv/Scripts/python.exe scripts/checksums.py
./.venv/Scripts/python.exe scripts/check_release.py
./.venv/Scripts/python.exe scripts/validate_clients.py --broker-directory dist/0.5.0.dev4 --artifacts .tmp/m2-clients --results-directory .tmp/m2-native --managed-audit --routing --electron .tmp/electron-lab/node_modules/electron/dist/electron.exe
./.venv/Scripts/python.exe scripts/validate_client_security.py --integration-report .tmp/m2-native/CROSS-LANGUAGE-RESULTS.json
./scripts/test_broker_apps.ps1
./.venv/Scripts/python.exe scripts/validate_routing.py --output .tmp/m2-performance.json
./.venv/Scripts/python.exe scripts/audit_publication.py --gitleaks .tmp/gitleaks/gitleaks.exe
```

Initial builds were superseded for necessary source changes found during boundary
review (non-dictionary adapter output and secret-shaped model rejection). Historical
version directories were not overwritten. Only the current unvalidated development
build was refreshed before final source/runtime verification.

## Security and compatibility evidence

Focused tests cover malformed/oversized fields, unknown capabilities, operation,
provider/model and mode denials, absent cloud permission, deny precedence, unsupported
adapters, explicit no-substitution, unavailable local candidates, controlled cloud
fallback, unknown outcomes/no replay, recovery after cache expiry, persistent quota
across restart, route-mode quota bypass attempts, concurrency, audit failure before
vault access, response type/usage/vector bounds, bounded health/discovery state and
managed audit rotation/correlation. Real named-pipe tests use the new client methods
and verify non-disclosure. Existing authentication/revocation/lifecycle/hostile tests
remain required in the final gate.

Mocks are not live validation. No paid cloud requests or real local model tests were
performed. POK adapter and real coach tests are **NOT_RUN**; the compatibility report
preserves moderation, trusted instructions, cancellation and monetary budget gaps.
M3, Windows 11, signing, separate-account isolation, long soak and provider-specific
live acceptance remain **NOT_RUN**. There is no M3 implementation in this mission.

## Performance (synthetic, memory audit)

400 routed requests (200 serial, 200 over 8 threads); traced peak 851,453 bytes,
current 649,195 bytes. Concurrent batch 0.1650 s (~1212 requests/s). Median/p95 ms:
contract validation 0.0093/0.0113; authorization/candidate filtering 0.0066/0.0068;
availability selection 0.0007/0.0008; discovery with memory audit 0.1257/0.1763;
full routing with memory audit 0.5785/0.9096. Single-host microbenchmark, not an SLA,
soak result or disk-fsync benchmark. M1's separate fsync measurements remain in its
historical report; managed audit compatibility is exercised by integration tests.

## Preservation and final gates

27 historical artifact hashes verified against existing manifests (root dist and
0.3.1/dev1/dev2/dev3). Historical release IDs/names/bodies/assets/digests remained
unchanged. `apy_key.txt` is ignored/untracked and never modified; package exclusion
checker may compare its contents only in memory without output. Production vault
entries and production broker PIDs 24596/10268 were untouched. No unknown file is
staged. Final native, artifact, CI, publication and fresh-recovery results follow
when executed; do not infer them from this in-progress report.


## Final local acceptance — PASS

- `scripts/test.ps1`: exit 0, **393 passed in 59.53 s**, no skips;
  **95.92%** aggregate statements; Ruff/strict mypy and all **18** critical-module
  >=95% gates passed. Routing module: 100% statement coverage (see coverage report).
- Reviewed source build/checksums/check_release: exit 0; four executable self-tests,
  wheel/sdist metadata, archive exclusions and embedded code/source equivalence passed.
- Six applications/five languages: exit 0, same broker PID **23700**, then **17628**
  after restart. Every application returned a validated routed mock response, legacy
  model listing and denial checks. C++ termination left survivors functional. 25
  synthetic generation calls; denied generation never reached the mock server.
- Managed M1 audit under routed traffic: health ready, zero rejected records,
  7 archives, 125115 record bytes under 131072, 283 retained correlated events.
- Hostile-server harness: exit 0, **60 cases passed** across five languages.
- Installed-wheel/frozen console+desktop acceptance: exit 0; independent process,
  denial, shutdown, restart and crash recovery passed with legacy configuration.
- Source Gitleaks: 173 Git-eligible candidates, zero findings; committed-history scan
  exit 0, zero findings. Final checkpoint scan is repeated before synchronization.

Artifacts: `dist/0.5.0.dev4/CAE-Broker.exe`, `CAE-Control-Center.exe`,
`CAE-Console-Client.exe`, `CAE-Desktop-Client.exe`,
`codex_api_engine-0.5.0.dev4-py3-none-any.whl`,
`codex_api_engine-0.5.0.dev4.tar.gz`, `SHA256SUMS.json`.
Lab/client packages are isolated in `.tmp/m2-clients/`; historical client packages
remain untouched. Executables are unsigned and local only. No stable release.
Raw local evidence: `.tmp/m2-acceptance-tests.log`, `m2-native/`, `m2-hostile.log`,
`m2-legacy-apps.log`, `m2-performance.json` and redacted scan reports. These ignored
machine-local files are not publication inputs; commands and summaries above are.
