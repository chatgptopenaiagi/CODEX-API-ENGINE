# Resume CAE development

- Project root on the original workstation: `I:\CODEX-API-ENGINE`.
- Canonical repository: https://github.com/chatgptopenaiagi/CODEX-API-ENGINE
- Development branch: `feat/security-registry`.
- Development version: **0.5.0.dev1**; client SDKs: **0.4.0**.
- Latest verified implementation: `b379795d109dbdfa62b079805d8db9aef3368457`.
- Checkpoint revision: resolve `git log -1 --format=%H -- docs/continuity`.
  A document cannot contain its own commit hash. Later checkpoint-only commits do
  not replace the implementation evidence above. Verify actual HEAD before editing.
- Last completed increment: application registry, runtime revocation, persistent
  minute/day quotas and concurrency limits; the broader v0.5 milestone is unfinished.
- Next milestone: **audit correlation, metadata enrichment and bounded rotation**.

## First implementation task

Inspect `src/cae/audit.py`, `access.py`, `broker_service.py` and their tests. Define
one broker-generated request correlation identifier across authorization and result
events. Add allowlisted decision/status/error-code/latency metadata without logging
prompts, results, headers or arbitrary exception text. Preserve existing consumers
and fail-closed audit behavior. Test denied operations never reach provider/vault
I/O. Then implement bounded disk retention and safe rotation, including concurrent
writers, restart and filesystem-failure tests. Do not change production audit files.

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
