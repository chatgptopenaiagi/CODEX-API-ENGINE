# Resume CAE development

Project root: `I:\CODEX-API-ENGINE`.
GitHub: https://github.com/chatgptopenaiagi/CODEX-API-ENGINE
Branch: `feat/security-registry`; keep PR #2 open/draft, never merge automatically.
Development version: **0.5.0.dev4**; existing client SDK contracts: **0.4.0**.
Starting checkpoint: `ac55a2fc29ed3d6e3b55e9afea7eea1e7f1440a1`.
Verified implementation SHA: `ee1947e7c467ee8de46e9acee7ba0e2176c51688`.
Preserve later commits; inspect `git log -1 --format=%H -- src/cae/routing.py`.
Checkpoint SHA: resolve `git log -1 --format=%H -- docs/continuity`.
Verify actual HEAD; a document cannot embed its own resulting commit hash.

- Last completed milestone: **M2 COMPLETE** under its documented mock-tested contract.
  393 tests, 95.92%, 18 critical gates, six routed clients, 60 hostile cases and
  independent GitHub/installed-wheel recovery passed. M1 remains complete.
- Next milestone: **M3 remaining recovery and artifact acceptance**. Real routed Qwen inference passed; M3 overall remains PARTIAL.
- Actual gate results: [ROUTING-M2](../validation/ROUTING-M2.md).

## First task

Read AGENTS.md and the current continuity files, then
[LOCAL-INFERENCE-M3](../validation/LOCAL-INFERENCE-M3.md). Verify Git status and
resolve this local checkpoint with `git log -1 --format=%H -- docs/continuity`.
Starting M3 commit was bf238e2773cc1ea39b0e684faa9ef8ab7b45b176; local source remains
0.5.0.dev4, but historical dev4 artifacts do not contain the model-ID fix.
The approved llama.cpp endpoint is 127.0.0.1:8080, exact model identity in the report.
Do not rediscover or download it. Five real routed calls and denial/timeout checks
passed; 399 regression tests passed. Preserve the running server and production broker.
Next address remaining M3 recovery/package acceptance; do not claim M3 complete.
Any rebuild must use a new development version/directory, preserving old artifacts.
This checkpoint is local only; no new GitHub synchronization or release is claimed.

```powershell
./scripts/resume-development.ps1
git status --short
git log -5 --oneline
git ls-remote origin refs/heads/feat/security-registry
./scripts/test.ps1
```

Rebuild only when source/artifacts differ or artifacts are absent:

```powershell
./scripts/build.ps1 -Executable
./scripts/build_clients.ps1 -OutputDirectory .tmp/m2-clients
./.venv/Scripts/python.exe scripts/checksums.py
./.venv/Scripts/python.exe scripts/check_release.py
```

Six-client/hostile/benchmark commands are in ROUTING-M2. Recovery prerequisites and
installation sequence are in RECOVERY_PROCEDURE.md. Routine tests need only mock
providers and synthetic credentials, never production keys or the production broker.

Never read during ordinary exploration, modify, delete, rename, move, publish or
package `apy_key.txt`; never change its ACL. Preserve production credentials,
enrollments, policy/log state, running operator broker and historical artifacts/tags.
Keep synthetic brokers isolated. No paid cloud calls, M3 model downloads, global PATH
changes, Codex changes, other-repository changes, force push, main merge or stable
release without the relevant explicit authorization. POK remains independent and
NOT_INTEGRATED. Windows 11, signing and strong same-user isolation are not established.

## Executable continuation directive

Read AGENTS.md and this checkpoint. Verify Git status/version/tests and current
acceptance evidence. Preserve unknown files and later commits. Select the first
unfinished authorized milestone; implement a bounded increment, test, record actual
results, update continuity and commit reviewed files. Do not repeat completed work,
modify production credentials or publish a release without authorization.
