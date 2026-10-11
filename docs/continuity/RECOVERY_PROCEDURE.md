# Recover without conversation history

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
read all ten continuity documents. Latest verified implementation is b379795;
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
./.venv/Scripts/python.exe scripts/check_release.py --directory dist/0.5.0.dev1
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

Select the audit increment in NEXT_SESSION.md. Implement, test, document actual
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
