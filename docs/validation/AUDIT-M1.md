# M1 audit increment — implementation and acceptance record

Status: **PARTIAL**. This increment implements request correlation and safe metadata
extensions. It does not complete bounded retention or crash-safe rotation.
Mission CAE-CONTINUATION-2026-10-11 continued across local midnight to 2026-10-12.

Starting checkpoint: `cfc04f6724d82ca7e3a63fa9daab436ea38e7bad`, branch
`feat/security-registry`. Development version: 0.5.0.dev2. Windows 10 build 19045
x64; Python 3.14.7; PowerShell 7.6.6. No new toolchain dependencies.

## Plan and implementation

1. Preserve audit JSONL schema fields and protocol v1 framing.
2. Establish broker-generated request identity before parsing/authentication; nested
   runtime operations reuse that context, independent threads receive distinct IDs.
3. Add allowlisted decision/status/error metadata and monotonic elapsed time. Never
   use a client-supplied ID as trusted audit identity or copy arbitrary exception text.
4. Validate new fields on reads, accepting old records without the optional fields.
5. Return fixed `audit_unavailable` with no provider result when the broker cannot
   record an audit outcome, rather than silently dropping the connection.
6. Run synthetic failure, real pipe, compatibility, packaging and leakage checks.

Changed modules: `audit.py`, `access.py`, `broker_service.py`. Existing event names
and fields remain; new `ipc_result` means result prepared, **not proof of delivery**.
Latency is elapsed since request context began, not provider-only billing latency.
Wire request IDs remain unchanged and separate from audit IDs. Events outside a
request have an empty request ID. Existing persisted records load with empty/default
new metadata. Audit consumers should tolerate additive fields/events.

## Executed evidence

- Baseline `./scripts/test.ps1`: exit 0, **218 passed**, **95.24%** statement coverage,
  Ruff/strict mypy and all 16 critical-module gates passed. No skips reported.
- Targeted `python -m pytest tests/test_audit_correlation.py -q --basetemp .tmp/m1-targeted`:
  exit 0, **18 passed**, no skips. Covers concurrent scopes, cleanup after exception,
  legacy records, corrupt metadata, error sanitization, quota denial, actual Windows
  pipe correlation and audit-failure denial before credential/provider access.
- Final `./scripts/test.ps1`: exit 0, **247 passed in 33.34s**, no skips,
  **95.36%** aggregate statement coverage. Ruff and strict mypy passed. All 16
  selected critical modules passed >=95%; audit.py measured **99.17%**.
- Process-exit and registry targeted tests: **24 passed**, exit 0.
- Windows lab-report failure/recovery regression tests: **2 passed**, exit 0.
- `scripts/build.ps1 -Executable`: exit 0; wheel/sdist and all four EXEs built
  in `dist/0.5.0.dev2/`; each EXE self-test passed. Existing versions preserved.
- `scripts/checksums.py`, `scripts/check_release.py --directory dist/0.5.0.dev2`
  and artifact credential/exclusion checks passed, exit 0.
- Final native harness: **six applications / five languages**, broker PID **27264**
  then **27852**, passed. Run with `--broker-directory dist/0.5.0.dev2
  --artifacts .tmp/m1-clients --results-directory .tmp/m1-corrected-validation
  --electron .tmp/electron-lab/node_modules/electron/dist/electron.exe`.
  The separate client artifact directory preserves original SDK builds; only the
  .NET lab application was rebuilt after its report-I/O fix.
- Hostile-server harness using the resulting CROSS-LANGUAGE-RESULTS.json:
  **60 passed**, exit 0, five languages. All providers mocked.
- Final redacted Gitleaks source scan: **164 Git-eligible files, zero findings**,
  exit 0. Only the 34 reviewed mission paths were staged; unrelated user files
  remain untracked. Protected input remains ignored and untracked.
- Historical v0.2.0/v0.3.1 release metadata/tag snapshots and local checksums,
  including the prior 0.5.0.dev1 artifact manifest, remain unchanged.

## Failures found and corrected

The prior checkpoint's push CI run 38176898988 failed its final shutdown assertion
after successful revocation; the parallel PR run passed. Supervisor polling treated
any transient pipe error as proof of exit. It now waits for the authenticated PID
with SYNCHRONIZE-only access and bounded timeout, releasing the handle. Tests cover
timeout, wait failure, absent process, denied access and invalid identity. No kill
right is requested and no production process is stopped.

One repeated six-client run failed the surviving-process assertion. Inspection
identified report publishers that exited on Windows sharing errors; the original
run did not record which client exited. The file-sharing hazard was reproduced
deterministically. An attempted share-delete reader did not solve it on this host
and was not retained. Python, Node and .NET lab loops now tolerate transient report
write errors; stale/missing reports still fail the unchanged acceptance criteria.
The harness now identifies exited clients in assertion output. A direct regression
test holds the report open, verifies the writer survives, releases it and verifies
the next report. Final six-client and hostile-server runs passed. No assertion was
removed or coverage threshold lowered.

Raw local logs: `.tmp/m1-baseline.log`, `m1-complete-quality.log`,
`m1-build-final.log`, `m1-corrected-clients.log`, `m1-corrected-hostile.log`;
failed run retained as `.tmp/m1-final-clients.log`. These are not committed.

## Security and remaining acceptance

The storage design remains append-only JSONL with bounded reads, not bounded disk
growth. Rotation, expiry, multi-process writer serialization, crash recovery,
partial writes, disk exhaustion and reparse-point race hardening are **NOT_IMPLEMENTED
or NOT_RUN for the new retention design**. Existing symlink checks do not establish
protection against hostile same-account path replacement. No audit directory was
migrated or production configuration changed.

Next M1 step: design and test an explicitly versioned retention configuration and
durability contract. Preserve existing file DACLs; serialize writers across processes;
bound total retained bytes/files; prevent deleting policy/quota/enrollment state;
inject interrupted rotation/restart failures and test real process termination.
Do not mark M1 complete or proceed to M2 on the basis of correlation alone.

Provider responses are mocked. Real inference, Windows 11 acceptance and POK adapter
acceptance are NOT_RUN. No paid cloud requests, production credential changes,
operator broker lifecycle operations, stable release or main merge are authorized.
