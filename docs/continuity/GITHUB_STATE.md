# GitHub checkpoint state

Canonical public source: https://github.com/chatgptopenaiagi/CODEX-API-ENGINE

Authenticated account verified with `gh auth status` / `gh api user`: chatgptopenaiagi.
Default branch remains `main`. Development branch: `feat/security-registry`.
Implementation commit `b379795d109dbdfa62b079805d8db9aef3368457` was pushed normally
and independently confirmed through the GitHub commits API. All three development
commits are preserved, including d969373 and 327bd2f. No force-push or main overwrite.

Draft PR: https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/pull/2

Initial CI runs: [push](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/actions/runs/38176501065)
and [PR](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/actions/runs/38176512518).
The initial PR run completed successfully; the initial push run was still running
at this snapshot. Later checkpoint commits trigger their own runs. Query current
checks with `gh pr checks 2` and `gh run list --branch feat/security-registry`.
The branch remains development, not promoted to main or declared a stable release.

Historical releases are v0.2.0 and v0.3.1. No new downloadable release is authorized.
Their tags and assets are preserved; metadata was snapshotted for before/after
comparison. Development binaries remain local ignored outputs.

## Repository discovery

GitHub metadata listed 19 account repositories. CAE documentation explicitly names
ARX and CREDID GUARDIAN CODEX, matching the public repositories
[ARX](https://github.com/chatgptopenaiagi/ARX) and
[CREDID-GUARDIAN-CODEX](https://github.com/chatgptopenaiagi/CREDID-GUARDIAN-CODEX).
Together with CAE these are confirmed relationships, not an authoritative set of five.
Other public candidates include agent-process-microscope, Codex-Launcher-Awarness,
CARE, HAAEP and CGCCHILD. Private repository metadata is not copied into public docs.
The operator explicitly deferred selection until they identify the five. Do not
modify, push or publish other repositories. No other repository was modified.
PR #2 must remain a draft; merging and stable releases are not authorized.
Keep CAE canonical; use dependencies/contracts
instead of duplicating source. See [ecosystem boundaries](../ECOSYSTEM.md).

## Verify the current checkpoint remotely

```powershell
git log -1 --format=%H -- docs/continuity
git ls-remote origin refs/heads/feat/security-registry
gh api repos/chatgptopenaiagi/CODEX-API-ENGINE/commits/feat/security-registry --jq .sha
```

Checkpoint commit SHA is recorded by Git rather than self-embedded in that commit.
Initial checkpoint `117ff2198ce43ffd8fbdc437eb693f3d3c7d2b4d` was verified via
GitHub API and a fresh remote clone; all ten documents were listed by the GitHub
contents API. The recovery-evidence commit follows that checkpoint without changing
runtime code. The final mission report records the exact synchronized revision. The independent
clone procedure is in RECOVERY_PROCEDURE.md. Future changes must refresh evidence
and compare actual HEAD; these documents are not a permanent assertion that an
arbitrary future branch tip passed the original tests.
