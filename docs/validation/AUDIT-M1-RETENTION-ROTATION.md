# M1 managed JSONL retention and rotation

Status: **M1 COMPLETE under the documented opt-in storage and process-crash contract**.

Development version: **0.5.0.dev3**. Starting revision:
`02153a7c5a8374c4e438fd7fd43e96c8778d9d03`, branch `feat/security-registry`.
Implementation revision: `git log -1 --format=%H -- src/cae/audit_storage.py`.
Final local acceptance results are recorded below; this is a development feature, not a
stable release or an independently reviewed security certification.

## Implementation and compatibility

`audit_storage.py` supplies a Windows file-backed sink behind the existing
`AuditLog`. `audit.py` retains event validation, broker-generated ContextVar IDs,
redaction and the legacy JSONL reader. `config.py` validates an optional TOML
section; `registry.py` preserves it during policy updates and applies its limits
to a separate administrative audit store. `access.py` includes storage status in
diagnostics and audits before a credential-presence probe. No wire framing,
enrollment format, quota database or provider adapter was replaced.

The implementation sequence was: recover and test baseline; specify ownership and
durability; implement file synchronization and recoverable intents; integrate
configuration/readers; inject failures and process termination; run regression,
native client, package and publication checks. See `tests/test_audit_storage.py`.

Missing `[audit]` preserves existing legacy behavior, including **unbounded legacy
disk logs**. There is no automatic production migration. Enable the managed mode
only through an explicit administrator configuration change and broker restart:

```toml
# Top-level table, not part of a [[providers]] or [[rules]] item.
[audit]
mode = "managed"
active_bytes = 1048576
total_bytes = 8388608
archive_count = 7
archive_age_seconds = 2592000
lock_timeout_ms = 2000
```

These are the defaults when `mode = "managed"` is present. Other modes and unknown
keys are rejected. Values must be integers (not booleans, strings, floats or NaN).
Legacy configurations remain loadable. Administrative configuration changes still
require restart; existing registry objects retain their selected audit sink.

| Setting | Accepted range | Contract |
|---|---|---|
| active_bytes | 4,096–16,777,216 | Hard logical record-byte limit per active file |
| total_bytes | 4,096–1,073,741,824; at least active_bytes | Hard managed record-byte limit after successful operations |
| archive_count | 0–64 | Hard after successful operations; at most one extra generation during interrupted rotation |
| archive_age_seconds | 0–315,360,000 | Event-driven limit; 0 disables age expiry only |
| lock_timeout_ms | 1–10,000 | Bound for each thread/OS lock acquisition; not a deadline for Windows filesystem I/O |

No setting disables size/count bounds. Zero archive count discards every closed
generation. Age pruning runs on append, managed reads and status inspection, not
on a timer: an idle store can retain expired files until its next operation. Age is
measured from the persisted archive creation time, not file mtime. Generations are
ordered by `(created_ns, name)`; timestamps never move backwards between rotations
even if the wall clock does. Clock rollback can delay expiry.

## Ownership and storage bounds

The broker uses `<runtime parent>/.cae/audit-managed/`; the administrative registry
uses `<broker configuration parent>/.cae/administration-managed/`. Limits apply
**separately to each store**, not to their sum. Neither includes quotas, enrollment,
policies, credentials, legacy logs or unknown files in its deletion scope.

A newly created store receives a protected DACL granting its Windows user and
SYSTEM access. Existing directory ACLs are not rewritten. Use administrator-owned
configuration under the established trusted Windows-user boundary.

Reserved filenames are `active.jsonl`, `state.json`, `state.new`, `writer.lock` and
`archive-<store UUID>-<generation UUID>.jsonl`. The bounded manifest records each
owned archive's NTFS file identity and creation time. Retention deletes only listed
archives with matching identities. It never glob-deletes or recursively removes
directories. Unknown files survive. A fresh store refuses to adopt existing logs
or unknown files. A reserved scratch manifest is recoverable during initialization.

Paths must remain beneath the fixed root; alternate streams, reparse components,
symlinks, nonregular files and hard-linked managed files are rejected. The root is
held open without delete sharing during operations. This is not protection against
all hostile code under the same Windows account; such code can tamper with files,
metadata or the process itself. Moving/restoring a store can invalidate recorded
file identities and require deliberate operator recovery.

For cooperative writers and unchanged valid limits, logical JSONL bytes remain at
most `total_bytes`. Rotation renames bytes instead of duplicating them. There are
at most `archive_count + 1` archives during an interrupted transaction, one active
file, two bounded manifests (at most 65,536 bytes each) and a zero-byte lock file.
Thus the logical owned-byte budget is `total_bytes + 131072`, excluding filesystem
allocation rounding/metadata. Unknown files, externally modified files and old
legacy stores are outside this bound. Reducing limits beneath an existing active or archived
file size fails closed; it does not truncate complete records to fit.

Memory holds one record (maximum **4,096 encoded bytes including LF**), bounded
manifest metadata (maximum 65 transient archive entries), and a bounded reader
deque. Default reader capacity is 1,000, configurable up to 100,000. Open handles
are scoped and closed on failure. Recovery scans at most one active file; archive
inspection can scan at most the configured total bytes. Ordinary appends stat at
most 64 retained archives, rather than reading all historical records or scanning
unknown directory contents. Filesystem latency is not a hard real-time guarantee.

## Rotation, synchronization and durability

Managed writes use a bounded per-AuditLog thread lock and a shared Windows byte-range
lock on `writer.lock`. Separate instances/processes use the same OS lock. Every
managed read, recovery, rename and prune participates in that lock. Process death
releases the OS lock. Overload can return `audit_unavailable` on lock timeout;
there is no unbounded writer queue inside the storage implementation.

Before an append would exceed the active threshold, persist and flush a rotation
intent. Close all active-file handles, rename to a new UUID destination, persist
the resulting manifest, create a new empty active file and persist its identity.
Prune before appending the next record. Windows `Path.rename` fails on an existing
destination, so collisions never overwrite files. Readers holding ordinary Python
file handles can block rename: that produces a visible failure and replayable intent.

Each event is validated and serialized before touching storage. Successful managed
append means the complete JSONL line was written, Python buffers flushed,
`os.fsync` completed and the stream closed. Manifest replacement uses a flushed
`state.new` and `ReplaceFileW` without flags that ignore ACL errors. Initial
publication uses non-overwriting rename. The replacement retains the old file DACL.

This is **process-crash recovery**, not a claim of power-loss or disk-controller
durability. A failed append may have written a complete record before reporting an
error (flush/close/unlock failure). Callers must not assume rollback or replay paid
operations. Uncommitted partial trailing bytes are discarded; valid preceding
records remain. Complete malformed records cause fail-closed operator-visible
degradation when checked during active recovery or archive reading. Ordinary
appends do not parse every archive; known expired archives may be pruned without
content validation. This is not continuous corruption detection. No exactly-once delivery guarantee is asserted.

## Recovery states

Recovery holds the same OS lock and is idempotent. Pending deletion records are
removed from the manifest after unlink; if unlink already happened, replay only
finishes metadata. Pending rotation accepts the old active file or the renamed
archive with the expected identity, never both. A missing active file is recreated
only when the committed state explicitly expects creation. Unexpected missing or
replaced files fail closed. A valid flushed `state.new` can recover a missing
manifest; incomplete first initialization can restart only before any logs exist.

| Interruption | Possible state and recovery | Loss/security effect |
|---|---|---|
| A before write; B serialization | Existing files unchanged | New event not accepted; protected work not started |
| C append | Unterminated tail | Discard tail, preserve preceding complete records |
| D before/during flush | Partial or complete final record | Event may survive despite failure; no automatic replay |
| E before rotation intent | Old active remains | Next append retries rotation |
| F archive rename | Pending intent plus old active or archive | Replay rename/metadata; collision fails closed |
| G archive exists, active not created | Manifest expects creation | Create empty active and record identity |
| H/I prune/unlink/metadata | Pending deletion, archive present or absent | Complete only the already-recorded deletion |
| J startup recovery | Same recorded intent, possibly incomplete scratch metadata | Repeat recovery; ambiguous/corrupt state needs operator intervention |

An expired/over-budget owned generation can be lost by design during retention,
including when the subsequent append fails. Audit evidence is not authoritative
authorization state. Deletion never affects quotas, policy or registry records.

## Filesystem failure matrix

All failures return fixed `audit_unavailable`, without filesystem paths or exception
text. Diagnostic status retains degradation until a successful append; read-only
inspection does not falsely clear write failure. Failures are not recursively audited.

| Operation | Covered failure / preserved state | Test evidence / recovery |
|---|---|---|
| CREATE | Incomplete initialization, reserved files, unsafe root | Fresh-root/reparse/init tests; retry or explicit intervention |
| OPEN | Real Windows sharing denial, identity mismatch, hard link | Open-sharing/path tests; close conflicting reader then retry |
| WRITE | Short write, malformed complete record, oversized input | Append-failure/corruption tests; recover partial tail only |
| FLUSH | Injected ENOSPC/fsync/flush failure | Fixed error; prior data retained; append may be ambiguous |
| CLOSE | Injected close error after actual handle close | Fixed error, no handle leak; reopen tested |
| RENAME | Before/after fault, abrupt process exit, real reader conflict | Persisted intent replay; no destination overwrite |
| REPLACE | Real open-manifest sharing conflict; missing old manifest | Retain scratch replacement, retry/recover validated manifest |
| LOCK | Actual competing process, bounded thread wait | Timeout fixed error; killed lock owner releases lock |
| UNLOCK | Injected error after actual unlock | Append can exist but caller receives failure; next call succeeds |
| STAT | Injected owned-stat failure, replaced file identity | No destructive action on mismatched file |
| LIST | Unknown file during initialization, junction root | Refuse adoption; ordinary writes do not directory-scan |
| DELETE | Injected before/after unlink, process exit after unlink | Replay pending deletion exactly within manifest scope |
| RECOVER | Partial tail, interrupted metadata/rotation/delete | Repeated recovery and actual process-exit tests |

Physical disk exhaustion, power cut, antivirus-controlled stalls and inaccessible
hardware were **NOT_RUN**. ENOSPC and permission/handle failures are bounded fault
injection or real Windows sharing tests, not claims of testing every storage driver.

## Fail-closed semantics and observability

Required authorization audit records still precede credential reads/provider
calls. Tests assert zero vault reads and zero provider calls on storage failure.
Credential-presence probes now also record their required event first. Broker
authentication/outcome failures retain existing fixed protocol errors and no result
payload. A previously dispatched provider call cannot be rolled back by a later
outcome-audit failure; that existing boundary remains explicit.

`AuditLog.storage_status()` exposes fixed health/failure categories, rejected count,
last recovery category, limits, logical sizes/count and rotation timestamp. Runtime
diagnostics add `audit_storage`; no private paths or record bodies are returned by
this status. Counters are per object/lifetime, not durable accounting. Diagnostics
that require successful authentication auditing still fail closed if storage is
unavailable; trusted local storage inspection remains possible.

`AuditLog.events()` preserves active-file reading. `events(include_archives=True)`
enumerates retained generations oldest-first followed by active records, bounded by
reader capacity. Runtime audit inspection uses this combined view with the existing
application filter. Ordinary tools can read each generation as legacy JSONL.

## Reproducible validation

All test state is repository-local, synthetic and isolated; local volume is NTFS. No production broker,
credential, enrollment, policy or log migration was performed. Host: Windows 10
build 19045 x64; Python 3.14.7; PowerShell 7.6.6. Windows 11 acceptance: **NOT_RUN**.
Existing .NET/Node/C++/Electron toolchains were reused; no persistent PATH changes.

```powershell
./scripts/build.ps1 -Executable
./scripts/test.ps1
.venv/Scripts/python.exe scripts/validate_audit_storage.py --output .tmp/retention-validation/PERFORMANCE.json
.venv/Scripts/python.exe scripts/validate_clients.py --broker-directory dist/0.5.0.dev3 --artifacts .tmp/m1-clients --results-directory .tmp/retention-validation-final --managed-audit --electron .tmp/electron-lab/node_modules/electron/dist/electron.exe
.venv/Scripts/python.exe scripts/validate_client_security.py --integration-report .tmp/retention-validation-final/CROSS-LANGUAGE-RESULTS.json
.venv/Scripts/python.exe scripts/checksums.py
.venv/Scripts/python.exe scripts/check_release.py --directory dist/0.5.0.dev3
.venv/Scripts/python.exe scripts/audit_publication.py --gitleaks .tmp/gitleaks/gitleaks.exe
```

For a fresh checkout, build client SDKs using `scripts/build_clients.ps1` and supply
its output to `--artifacts`; `.tmp/m1-clients` is this workstation's preserved lab
build. Follow `docs/continuity/RECOVERY_PROCEDURE.md` for toolchain restoration.

Baseline: **247 tests, 95.36%**, existing Ruff/mypy/16 critical coverage gates passed.
Intermediate regression: **295 tests, 95.61%**, 17 critical modules >=95%; no skips.
Final runtime results: **PASS — 299 tests in 59.38 s, 95.64% coverage**, no skips;
Ruff and strict mypy passed; all 17 selected critical modules >=95%.
The new storage module has 96.86% statement coverage (350 statements, 11 missed).
Six applications/five languages passed against the same built managed-audit broker
PID 21740, then recovered on PID 28968. Termination survival, denied admin/spoofed
identity/provider operations, clean shutdown and restart passed. The retained
store ended with 7 archives, 120,157 record bytes (limit 131,072), 354 readable events
and no reported rejected events. Mock HTTP only; no live/cloud model claims.
**60 hostile-server cases passed** across five languages. Source publication scan:
168 candidate files, Gitleaks, zero findings; committed-history scan found no leaks.
Historical checksums: 24 artifacts verified; historical release IDs/assets/digests
unchanged. Package checks **PASS**: wheel/sdist metadata, archive credential exclusion,
all four executable self-tests, runtime/source equivalence and checksums. Existing
console/desktop-client acceptance also passed installed-wheel access, denial,
termination survival, shutdown/restart and crash recovery with legacy configuration.
Protected DACL inspection on isolated NTFS storage: protected=true, two explicit
rules, zero inherited rules. Existing root ACLs are a trusted operator prerequisite;
they are not automatically repaired or strengthened. Windows-native modules are
loaded lazily so the legacy memory audit import does not newly depend on msvcrt.
Remote synchronization and independent recovery are recorded in GITHUB_STATE.md.

A native acceptance run exposed a harness race: a report written after restart
could still describe a pre-restart request. The harness now waits for a report
whose broker PID differs from the old process as well as a fresh timestamp; a
regression test demonstrates the stale report is rejected. This strengthens the
existing restart assertion rather than accepting stale client evidence.

Measured 229 synthetic events, 8 threads, 4 KiB active/16 KiB total: serial median
43.707 ms, p95 267.528 ms; concurrent median 623.406 ms, p95 784.015 ms; startup
17.614 ms; archive enumeration 20.302 ms; three-archive pruning 370.315 ms. These
final measurements include rotation/retention, fsync and uncontrolled host load;
they are not an SLA. Reproduce with the benchmark above. Frequent tiny-file rotation
is deliberately stressful; defaults use 1 MiB generations. Further performance
optimization must preserve this durability contract.

Development artifacts belong only in `dist/0.5.0.dev3/`: four existing EXE targets,
wheel, source distribution and SHA256SUMS.json. Executables remain unsigned.
Previous development packages and historical releases are preserved. No stable
release, main merge or new provider capability is authorized by this validation.

## References and remaining limits

Windows operation semantics were checked against Microsoft's documentation:
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew),
[ReplaceFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew),
[FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers),
and [file locking](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex).
No write-through guarantee is inferred from ReplaceFile flags or Python close.

Legacy stores remain opt-out/unbounded; managed mode requires an operator change
and restart. No automatic archival import or repair of fully corrupted records.
No same-user hostile-process isolation, power-loss certification, Windows 11
acceptance, long soak, cryptographic audit authenticity or filesystem-independent
file identity guarantee. Storage permission failures are visible and fail closed;
the implementation does not relax ACLs or disable Windows protections to recover.
