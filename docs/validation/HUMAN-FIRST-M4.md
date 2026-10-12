# M4 human-first administration and distribution — PARTIAL

Final preservation: d97e9cf017442c34116cef791d12003f5310c68e was pushed and recovered
in a fresh GitHub clone. Six primary entry-point documents matched; checkpoint
version/history/reference checks and read-only resume passed without production
credentials. All 90 pre-existing artifact hashes, release identities and original
production broker/Qwen process identities remain unchanged. Final source/history
scans passed with zero findings (194 eligible files); five user files remain
untracked. The subsequent evidence-only checkpoint has its own CI; verify it rather
than treating local tests as CI. No release, stable promotion or main merge occurred.

Starting commit: 25e3fe8161d1d4228231427269169471f0e72ed7.
Branch: feat/security-registry. Entry version: 0.5.0.dev5.

Phases A/B PASS: local and GitHub heads match; authenticated account is
chatgptopenaiagi; PR #2 is open/draft and both checkpoint CI runs passed.
Tracked tree is clean; five pre-existing user files are untracked and preserved.
Read-only resume script passed. Existing reports were inspected, not relabeled as
new test executions. M3's 414 tests/95.95% remain historical at this phase.

Phase C: M0–M7 history, roadmap, versioned JSON checkpoint and reusable resume
directive added. M0 is retrospective; M7 is proposed, not implemented.

M4 implementation, GUI acceptance, new packages, license/privacy audit and public
download acceptance: NOT_RUN at this phase. RELEASE_NOT_PUBLISHED.
No installer exists. WINDOWS_11_NOT_RUN. No production broker/Qwen action,
credential modification, global environment change, main merge or release.

Next: extend existing Control Center through authenticated registry APIs, preserving
trusted in-process functions and making missing broker configuration actionable.

## Implemented increment — M4 remains PARTIAL

Version 0.5.0.dev6. Runtime build revision:
`5a0020ca674d157c1213572ac7f7910157805ed5`.
Candidate source archive revision: `d36ea832073be86b545e2c182196515f4003a5ba`.
Final checkpoint SHA is resolved by `git log -1 --format=%H -- docs/continuity`;
remote synchronization and independent recovery are checked after committing.

New Broker/Applications/Help pages preserve the five existing in-process pages.
Explicit operator selection verifies and pins image/hash/pipe/runtime; remembered
portable selection restores offline and is checked again before use. No scans,
self-enrollment, process start/stop or provider probes. Registry inspection and
confirmed registration/revocation use existing authenticated ApplicationRegistry.
Registration grants no provider access; revocation reports effective timing.
Errors use fixed guidance, not exception contents. GUI close leaves brokers alive.

Missing: guided initial broker provisioning, graphical authorization/provider/
routing/quota editing, broker audit viewer and full beginner workflow acceptance.
The retained legacy pages are explicitly labeled as separate in-process operations.
M4 is not complete; M5 installer NOT_IMPLEMENTED; M6/M7 remain as roadmap records.

## Executed matrix

| Category | Result |
|---|---|
| Source/quality | PASS: 421 tests in 82.45s, 96.04% statement coverage, all 18 critical gates; Ruff and strict mypy |
| New operator backend | PASS: pin tampering, malformed/oversized selection, unknown-file preservation, unauthorized registry access; 100% measured module statements |
| GUI | PASS: actual Tk construction, first missing config, confirmation, admin list/register/revoke, unavailable broker guidance, saved restart and malformed saved state; main-thread cleanup |
| Four frozen EXEs | PASS: self-tests, archive inspection and runtime/source code identity |
| Wheel | PASS: fresh venv, --no-index --no-deps, -I site-packages import, operator module and CLI dev6 |
| Python sdist | PASS: archive and runtime-source consistency |
| Complete source ZIP | Created from immutable Git tree d36ea83, not untracked workspace files; includes build/test/docs/license files |
| Portable independent copy | PASS: SHA match, extraction outside repository, no-flag packaged GUI window titled CAE Control Center · 0.5.0.dev6, clean window close, self-test; no external Python needed |
| Native compatibility | PASS: six actual Python/C#/C++/Node/PowerShell/Electron apps, mock providers, broker PID 25444 then 8872 |
| Hostile server | PASS: 60 cases across five SDK languages |
| Packaged recovery | PASS: established 18 synthetic scenario groups against dev6; report .tmp/m3-packaged-cfad6d988fce4386aec14ce1af46bdfe/RESULTS.json |
| Real Qwen/cloud | NOT_RUN in M4; historical M3 evidence preserved, no server modification or paid call |
| Installer / Windows 11 | NOT_IMPLEMENTED / NOT_RUN |
| GitHub downloaded M4 binaries | NOT_RUN: release not published |

The initial prebuild regression run had 419 passes, one expected missing-artifact
skip and one GUI worker failure caused by delayed Tk garbage collection from the
new test. Explicit main-thread cleanup fixed the isolation issue. The final full
421-test run had no skips or warnings; no assertion or coverage floor was weakened.
An earlier GUI test deadline of two seconds was corrected to allow the documented
three-second missing-broker timeout; it still asserts bounded completion.

## Artifact identity

Directory: `dist/0.5.0.dev6/`, distinct from every previous build. All four EXEs,
wheel and sdist are indexed by its SHA256SUMS.json. Candidate ZIP/source archive,
SHA256SUMS.txt/json and RELEASE_MANIFEST.json are under `portable-candidate/`.
The latter records immutable runtime/archive commits and is explicitly
BLOCKED_NOT_FOR_PUBLICATION. Later documentation checkpoints do not relabel binaries.

Broker SHA256: `20bab41df2d27baa12edf8dff0d1b91a81ef8647e8a3eddfdf19612783f917be`.
Control Center SHA256: `6f710e6d861f708c10a8816062610b0499e43a2794b5fdfd596fc877f9592c03`.
No installer placeholder, signing claim or overwritten historical package.

## License and privacy review — publication BLOCKED

CAE remains MIT. Actual installed Python LICENSE and PyInstaller COPYING were
included in the local candidate. PyInstaller's [official exception](https://pyinstaller.org/en/stable/license.html)
permits bundling subject to dependency licenses; Python documents [incorporated
software obligations](https://docs.python.org/3.14/license.html). The exact packaged
DLL inventory includes Tcl/Tk, OpenSSL, SQLite, libffi, libtommath, compression and
Microsoft runtime/API-set components. Full notice/redistribution mapping is not
complete. THIRD_PARTY_NOTICES.txt clearly records PARTIAL, not clearance.

Installer evaluation is deferred to M5 rather than adding a global tool. Inno
Setup's [current licensing information](https://jrsoftware.org/isorder.php) must
be considered before selecting it; no installer is installed or represented as ready.

No telemetry was added. Startup is offline. Status uses local authenticated IPC;
only explicit legacy provider actions or authorized broker operations can use a
provider network connection. Portable selections contain machine paths/identity,
not secrets, and are Git-ignored. No production configuration is in candidate ZIPs.
Source Gitleaks scan at runtime commit: 191 eligible files, zero findings. Candidate
archive Gitleaks scan: zero findings. Existing artifact checker passed exact-secret
exclusion in memory without emitting protected values. Final source/history scan
is required before push. Zero findings are not a complete security proof.

**RELEASE_NOT_PUBLISHED.** Required exact runtime notices and complete first-run
provisioning acceptance are missing. Operator review and completion of those gates
are required before reconsidering a development prerelease; stable release and
main merge remain unauthorized. This is not a successful public-download mission.

## Reproduction and retained evidence

```powershell
./scripts/build.ps1 -Executable
./scripts/test.ps1
./.venv/Scripts/python.exe scripts/checksums.py
./.venv/Scripts/python.exe scripts/check_release.py
./.venv/Scripts/python.exe scripts/check_artifacts.py --directory dist/0.5.0.dev6
./.venv/Scripts/python.exe scripts/check_checkpoint.py
./.venv/Scripts/python.exe scripts/validate_clients.py --broker-directory dist/0.5.0.dev6 --artifacts .tmp/m2-clients --results-directory .tmp/m4-native --managed-audit --routing --electron .tmp/electron-lab/node_modules/electron/dist/electron.exe
./.venv/Scripts/python.exe scripts/validate_client_security.py --integration-report .tmp/m4-native/CROSS-LANGUAGE-RESULTS.json
./.venv/Scripts/python.exe scripts/validate_m3_packaged.py --broker-directory dist/0.5.0.dev6
```

Do not rebuild over existing artifacts. Fresh recovery first builds client packages
using the established scripts; the local .tmp paths are not remote dependencies.
Candidate packaging refuses an existing output directory:
`scripts/package_portable.py --build-source 5a0020c`.
Local logs: .tmp/m4-build.log, m4-full-tests.log, m4-native/, m4-hostile.log,
m4-fresh-copy.json, m4-candidate-scan.json. The external fresh-copy directory is
recorded in .tmp/m4-external-acceptance-path.txt and preserved. No global dependency,
PATH/security/CUDA/PyTorch/production process modification was made.
