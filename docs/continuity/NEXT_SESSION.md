## Experimental preservation checkpoint (2026-10-12)

The explicit preservation-only mission supersedes the earlier M4 completion-dependent
publication hold. No runtime source or existing binary was changed or rebuilt.
Published experimental prerelease (30 assets; all download hashes PASS): `v0.5.0.dev6-preservation`, source `2a300a0d96a0e8f2ad102940e4a9775d5d256608`;
binary build `5a0020ca674d157c1213572ac7f7910157805ed5`. See
[the preservation evidence](../validation/PRESERVATION-0.5.0.dev6.md) for actual
publication/download status and [artifact inventory](../validation/DEV6_ARTIFACT_INVENTORY.json).
M0-M3 remain complete within recorded scope; M4/M6 PARTIAL, M5/M7 PLANNED.
The first future development task remains confirmed authorization/routing/quota GUI
forms, then safe first-run provisioning. Do not develop during preservation.
Installer, signing, Windows 11 and POK integration remain incomplete/unverified.
Earlier RELEASE_NOT_PUBLISHED/BLOCKED statements below describe historical M4
candidate gates, not a prohibition on this authorized experimental preservation.

# Resume CAE: M4 remains PARTIAL

Read AGENTS.md and this file first. Then read CAE_CHECKPOINT.json, the M0–M7
history/roadmap, current state, limitations and HUMAN-FIRST-M4.md under validation.

Repository: https://github.com/chatgptopenaiagi/CODEX-API-ENGINE
Branch: feat/security-registry. Version: 0.5.0.dev6. PR #2 stays open/draft.
- Next milestone: **M4 PARTIAL — finish administration and publication gates**.
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
