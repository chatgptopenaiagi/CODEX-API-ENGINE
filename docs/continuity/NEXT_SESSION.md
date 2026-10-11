# Resume CAE development

- Project root on the original workstation: `I:\CODEX-API-ENGINE`.
- Canonical repository: https://github.com/chatgptopenaiagi/CODEX-API-ENGINE
- Development branch: `feat/security-registry`.
- Development version: **0.5.0.dev2**; client SDKs: **0.4.0**.
- Starting verified checkpoint: `cfc04f6724d82ca7e3a63fa9daab436ea38e7bad`.
- Current implementation revision: `git log -1 --format=%H -- src/cae`.
- Checkpoint revision: resolve `git log -1 --format=%H -- docs/continuity`.
  A document cannot contain its own commit hash. Later checkpoint-only commits do
  not replace the implementation evidence above. Verify actual HEAD before editing.
- Last completed increment: audit request correlation and fail-closed audit error
  responses; process-exit confirmation fixes a previously observed shutdown race.
  M1 as a whole remains PARTIAL.
- Next milestone: **M1 bounded retention and crash-safe rotation**.

## First implementation task

Request correlation is implemented and tested; do not repeat it. Read
[the M1 report](../validation/AUDIT-M1.md), then inspect `src/cae/audit.py` and
existing producers/consumers. Define explicit retention configuration and a
crash-durability contract before implementing bounded file/byte retention, safe
rotation, cross-process serialization and reparse-point defenses. Preserve file
DACLs, legacy records and fail-closed errors. Test interrupted writes/rotation,
process termination, restart, disk/access failures and concurrent writers using
isolated synthetic state. Audit evidence must never share deletion scope with
quota, policy or enrollment state. M2 remains blocked on completing M1 acceptance.

## Read and verify first

Read [current state](CURRENT_STATE.md), [unfinished milestones](UNFINISHED_MILESTONES.md),
[limitations](KNOWN_LIMITATIONS.md), [recovery](RECOVERY_PROCEDURE.md), root AGENTS.md,
ARCHITECTURE.md and SECURITY.md. Protocol and SDK contracts live in
[BROKER_PROTOCOL](../BROKER_PROTOCOL.md) and [CLIENT_SDKS](../CLIENT_SDKS.md).

```powershell
./scripts/resume-development.ps1
git status --short
git log -5 --oneline
git ls-remote origin refs/heads/feat/security-registry
```

On the original workstation, validated artifacts already exist. Run
`./scripts/test.ps1`; do not rebuild them without cause. For a fresh checkout, follow
the dependency/build sequence in RECOVERY_PROCEDURE.md before the full test gate.
Cross-language and hostile-server commands are in VALIDATION_EVIDENCE.md.

## Restrictions and blockers

Never read during ordinary exploration, modify, delete, rename, move, commit,
publish or package `apy_key.txt`. Do not change production Windows credentials,
Codex authentication, or the operator's existing broker. Tests require unique
synthetic state and pipes. Preserve v0.2.0/v0.3.1 tags/assets and existing history.
Do not force-push. Do not stage unrelated untracked user files.

No real local model or Windows 11 acceptance has been validated. Same-user hostile
process isolation, signing and independent security review remain open. GitHub CI
status is a separate check; see GITHUB_STATE.md and the current PR checks. The exact
five-repository requirement is explicitly deferred by the operator; do not modify,
push or publish other repositories until separately authorized. Keep PR #2 a draft;
do not merge it or publish a stable release during this mission.

## Continuation directive

Read AGENTS.md and this file. Verify Git status, actual HEAD, package version and
available tests. Do not repeat completed work. Select the next unfinished milestone
above, implement a bounded increment, execute its tests and compatibility/security
gates, document measured results and commit locally. Preserve production credentials
and the operator broker. Do not publish a release without explicit authorization.
