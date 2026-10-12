# Resume CAE development

Root: `I:\CODEX-API-ENGINE`.
Repository: https://github.com/chatgptopenaiagi/CODEX-API-ENGINE
Branch: `feat/security-registry`; PR #2 must stay open/draft.
Development version: **0.5.0.dev5**; client SDK contract: **0.4.0**.
Latest checkpoint: resolve `git log -1 --format=%H -- docs/continuity`, then compare
HEAD and remote. Preserve later commits and unknown files. Runtime build source:
bf6107f; original exact-model fix: 9b31d1460c64b255287e0a9cd7cdbf26b6e2bfee.

- Last completed milestone: **M3 COMPLETE** within its packaged/isolated-recovery contract.
- Next milestone: **M4 CENTRALIZED ADMINISTRATION**. Do not repeat M1/M2/M3.
- Evidence: [packaged M3 report](../validation/LOCAL-INFERENCE-M3-PACKAGED.md).

Read AGENTS.md, CURRENT_STATE.md, UNFINISHED_MILESTONES.md and KNOWN_LIMITATIONS.md.
Do not repeat M1/M2 or claim real Qwen is untested: one dev5 console/broker call
passed. The operator's llama.cpp at 127.0.0.1:8080 is read-only to development;
never restart/reconfigure it or download weights. Real-server outage/restart is
NOT_RUN. Fault injection uses only disposable loopback subprocess endpoints.

```powershell
./scripts/resume-development.ps1
git status --short
git log -5 --oneline
git ls-remote origin refs/heads/feat/security-registry
./scripts/test.ps1
./.venv/Scripts/python.exe scripts/validate_m3_packaged.py --broker-directory dist/0.5.0.dev5
```

The last command is mock-only. Artifacts: dist/0.5.0.dev5. Preserve older outputs;
future runtime changes require distinct versions/directories. Fresh prerequisites:
RECOVERY_PROCEDURE.md and ENVIRONMENT_STATE.md. Package checks: check_release.py,
check_artifacts.py; source safety: audit_publication.py (all under scripts/).

Never modify/display/publish/delete apy_key.txt. Preserve production vault, broker,
enrollment/audit state, historical tags/releases and unknown user files. No paid
cloud calls, global PATH/security/Codex/POK changes, force push, main merge or stable
release. Interpreter enrollment is not hostile same-user isolation. Windows 11,
installer, signing and long-soak acceptance remain unverified.

Continuation directive: verify source/tests; implement only the next unfinished
authorized milestone; test, document actual evidence, commit reviewed work. Never
publish releases without separate authorization.

First M4 task: inspect existing Control Center, registry and administrative trust
contracts; implement a read-only operator application-registry/broker-status view
with an isolated test broker before introducing security-sensitive GUI mutations.
M4 was not implemented in the M3 mission. Verify current GitHub checks before edits.
