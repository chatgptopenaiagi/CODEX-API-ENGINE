# Recover without conversation history

## M4 current checkpoint

Current M4 recovery: read AGENTS.md, NEXT_SESSION.md, CAE_CHECKPOINT.json, MILESTONE_HISTORY_M0_M7.md and MASTER_ROADMAP_M0_M7.md. Verify Git HEAD/remote and version dev6. Artifacts are local-only; rebuild with existing scripts when absent. Routine tests need no production credentials. No public M4 prerelease exists; the portable candidate is blocked, not a release.


## Locate or independently recover source

On the original machine, open `I:\CODEX-API-ENGINE`. First read AGENTS.md and
NEXT_SESSION.md and run `./scripts/resume-development.ps1`. Inspect local changes;
never reset, clean or delete untracked files to make recovery convenient.

For a fresh checkout, clone the canonical public branch into a **new unused path**:

```powershell
git clone --branch feat/security-registry --single-branch https://github.com/chatgptopenaiagi/CODEX-API-ENGINE.git CAE-recovery
Set-Location CAE-recovery
git status --short
git log -5 --oneline
git ls-remote origin refs/heads/feat/security-registry
./scripts/resume-development.ps1
```

Compare local HEAD to the remote branch, inspect later commits if different, and
read all ten continuity documents. The mission started at checkpoint cfc04f6;
checkpoint-only changes may follow it. Do not automatically reset to old hashes.
Existing checkout updates use reviewed fetch/fast-forward operations after inspecting
working state. Preserve development branches and release tags.

## Restore dependencies and build only when artifacts are absent

Prerequisites: Windows x64, Python 3.14 launcher, PowerShell, .NET SDK 10.0.401 with
.NET 8 runtime, Node 26.8.1, clang/LLD, MSVC x64 build tools and Windows SDK. See
ENVIRONMENT_STATE.md and scripts/build_clients.ps1 for actual pinned inputs.
Internet access is needed for dependencies. No production API key is needed.

```powershell
$env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH = 'false'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE = 'false'
./scripts/setup.ps1
./scripts/build.ps1 -Executable
./scripts/build_clients.ps1
./scripts/test.ps1
./.venv/Scripts/python.exe scripts/check_release.py --directory dist/0.5.0.dev5
```

Setup creates `.venv` and installs editable engine/dev dependencies; client build
creates the client packages. Facade unit tests load their source explicitly; the
process harness installs wheels into its own isolated environment. Never copy the original `.venv`
or production `.cae` state. Build outputs are version-specific and Git-ignored.
For optional Electron acceptance explicitly run `./scripts/setup_electron_lab.ps1`,
then the six-client and hostile-server commands in VALIDATION_EVIDENCE.md. Without
Electron the harness checks five languages, not six applications.

These harnesses create unique synthetic enrollment, pipe and mock-provider state.
Never substitute the production broker/configuration. A fresh clone intentionally
lacks provider keys and local enrollment. Real cloud/local inference is separate
from routine acceptance and requires specifically justified validation.

## Continue and preserve

Select the next unfinished task in NEXT_SESSION.md; M1 and the M2 routing implementation must not be repeated. Implement, test, document actual
results and commit only reviewed source. Run redacted Gitleaks source/history scans
and inspect staged paths before any public synchronization. Never commit dist,
environment files, private enrollment or protected input. No destructive Git
commands or automatic public release. GitHub source synchronization and release
publication are distinct authorizations.

## Recovery acceptance

A remote clone must contain AGENTS.md, all ten continuity files and the resume
script; its commit/version must match the verified remote branch. Run the script,
check linked source/test/build paths and verify that no production credential is
needed to understand or reconstruct the state. This checkpoint mission verifies
source recovery without rebuilding already validated local milestones. A full
clean-room toolchain installation/build remains a separate validation claim.

Executed recovery on 2026-10-11: a fresh clone directly from GitHub recovered
`117ff2198ce43ffd8fbdc437eb693f3d3c7d2b4d` on `feat/security-registry`.
All ten documents, AGENTS.md and the resume script matched (normalizing Windows
checkout line endings). Relative links and referenced build/test/source paths
resolved. The resume script reported 0.5.0.dev1 and the expected branch/commit,
identified the audit milestone, and left the checkout clean. No `.venv`, `.cae`
or protected credential file existed there. No production state was required.
This is verified source/checkpoint recovery, not a new clean-room executable build.

M1 managed-storage acceptance is reproduced with the commands in
[the storage report](../validation/AUDIT-M1-RETENTION-ROTATION.md). No production
credentials or running production broker are needed. Retain historical artifacts.

Current routed six-client acceptance uses `--routing --managed-audit`; see ROUTING-M2.md
under docs/validation for the complete command and isolated artifact paths.

M3 packaged recovery: `scripts/validate_m3_packaged.py --broker-directory dist/0.5.0.dev5`.
This is mock-only. `--real-qwen` makes one specifically approved local call; it never
starts/restarts/discovers servers. See the packaged M3 report.
