# Resume CAE: M4 remains PARTIAL

Read AGENTS.md and this file first. Then read CAE_CHECKPOINT.json, the M0–M7
history/roadmap, current state, limitations and HUMAN-FIRST-M4.md under validation.

Repository: https://github.com/chatgptopenaiagi/CODEX-API-ENGINE
Branch: feat/security-registry. Version: 0.5.0.dev6. PR #2 stays open/draft.
Latest checkpoint: resolve `git log -1 --format=%H -- docs/continuity` and verify
remote HEAD. Runtime build commit: 5a0020ca674d157c1213572ac7f7910157805ed5.
Candidate source archive: d36ea832073be86b545e2c182196515f4003a5ba.

M0–M3 remain complete within recorded contracts. M4 adds explicit pinned broker
selection/restore, status and registry list/register/revoke. No automatic grants.
421 tests/96.04%, 18 critical gates, six mock clients/60 hostile cases, independent
wheel and fresh-copy packaged GUI startup passed. Read the report for exact scope.

First remaining task: extend existing ApplicationRegistry authorization through
confirmed GUI forms with bounded routing/model/quota inputs; test operator denial
and unchanged existing rules. Then complete safe first-run provisioning and broker
provider/audit views. Do not repeat completed broker/routing/inference work.

RELEASE_NOT_PUBLISHED: incomplete exact bundled-runtime license inventory and
first-run provisioning acceptance. Local dev6 candidate is marked blocked.
No installer, Windows 11, signing, long soak or POK adapter claim. M5–M7 remain later.

Run scripts/resume-development.ps1, inspect Git status and version, then use
scripts/test.ps1 (build missing artifacts first). Full prerequisites and commands
are in RECOVERY_PROCEDURE.md. Never reset/clean unknown files.

Preserve apy_key.txt without reading/displaying/modifying/publishing it; preserve
production credentials, broker/enrollment/audit state and operator Qwen server.
No Codex/global PATH/security/CUDA/PyTorch/other-repository changes or paid cloud.
Use isolated synthetic tests. No force push, main merge or stable release.
Document/test/commit reviewed work; prerelease publication requires all gates.
