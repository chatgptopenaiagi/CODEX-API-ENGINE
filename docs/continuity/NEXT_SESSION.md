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
- Next milestone: **M3 REAL LOCAL-MODEL VALIDATION**. No real inference was tested.
- Actual gate results: [ROUTING-M2](../validation/ROUTING-M2.md).

## First task

Read AGENTS.md, CURRENT_STATE.md, UNFINISHED_MILESTONES.md, KNOWN_LIMITATIONS.md,
[capability routing](../CAPABILITY_ROUTING.md) and the M2 report. Verify Git status,
branch, HEAD, package version and current remote checks. Do not repeat implemented
M1 storage or M2 routing. First verify current GitHub CI and checkpoint consistency;
then identify an explicitly available, operator-approved local inference endpoint.
Do not change that endpoint or other environments. M3 must use an operator-approved
local model; never download weights or claim real inference from mock tests.

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
