# GitHub checkpoint state

## M2 implementation synchronized and recovery verified

0.5.0.dev4 is locally validated: 393 tests, 95.92%, 18 critical gates, six routed
mock clients, 60 hostile-server cases and package/legacy acceptance. Approved
destination: feat/security-registry, existing draft PR #2. Starting remote checkpoint
ac55a2fc29ed3d6e3b55e9afea7eea1e7f1440a1. No main merge or release. Concrete
implementation SHA: `ee1947e7c467ee8de46e9acee7ba0e2176c51688`. A fresh GitHub clone matched it,
read all continuation records and installed/verified the wheel independently.
Ten synthetic routed requests, cloud denial and managed audit recovery passed.
Final checkpoint SHA is `git log -1 --format=%H -- docs/continuity`; verify remote
HEAD and current CI separately. Source CI was pending when this record was written.

## Verified M1 implementation synchronization — 2026-10-12

Implementation commit `9768e4aa40f1242895c4bfa320703375b8716a63` was pushed normally to
`feat/security-registry` and independently matched through `git ls-remote` and a
fresh single-branch GitHub clone. That checkout read all 11 instruction/checkpoint
files, ran the read-only resume script, verified version 0.5.0.dev3 and the M2 next
step, and matched its source to the development wheel. A fresh local virtual
environment installed that wheel without dependencies/source imports and passed
an isolated managed-storage smoke test. No credential file existed in the clone.
Recovery: **PASS**. Source/runtime validation: **299 tests, 95.64%**, 17 critical
gates, six actual applications and 60 hostile-server cases passed locally.

GitHub runs for this implementation were in progress when this checkpoint was
written: [push](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/actions/runs/38181832753)
and [PR](https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/actions/runs/38181835171).
This documentation-only checkpoint triggers its own checks; query the latest head.
Do not infer CI success from local validation. PR #2 remains draft/open against
main; no merge or release was performed. Final checkpoint SHA is resolved with
`git log -1 --format=%H -- docs/continuity` and must match the remote branch.


## 0.5.0.dev3 synchronization

Authorized destination remains `chatgptopenaiagi/CODEX-API-ENGINE`, branch
`feat/security-registry`, draft PR #2. Final commit/remote verification is recorded
after validation; use `git ls-remote origin refs/heads/feat/security-registry` and
compare local HEAD. Do not merge, force-push or publish release binaries.
Historical v0.2.0/v0.3.1 releases and tags remain protected.

## Post-checkpoint development

0.5.0.dev2 is a partial M1 increment on the same development branch. Do not merge
draft PR #2 or publish a release. Latest implementation is obtained from Git history;
the dated original checkpoint below remains preserved. One checkpoint push CI run
38176898988 failed shutdown confirmation despite a passing PR run; the lifecycle
race is fixed and locally tested in this increment. See [M1 report](../validation/AUDIT-M1.md).
Query current PR checks rather than treating older CI results as current evidence.

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
