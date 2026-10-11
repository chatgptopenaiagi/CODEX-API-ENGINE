# Environment and hygiene

Observed 2026-10-11; no personal tokens or full PATH values are recorded.

| Tool | Actual local version |
|---|---|
| OS | Windows 10 x64, build 19045 (Windows 11 remains target) |
| PowerShell | 7.6.6 |
| Python | 3.14.7, repository `.venv` |
| .NET SDKs | 5.0.416, 8.0.425, 10.0.401, 11.0.100-preview.7.26381.103 |
| Selected .NET SDK | 10.0.401 via `clients/global.json`; clients target .NET 8 |
| Node | 26.8.1 |
| C++ | clang 22.1.8; existing MSVC 14.51 / Windows SDK toolchain |
| Electron | 44.7.0, repository-local lab runtime |
| Python validation/build | pytest 9.1.1, pytest-cov 7.1.0, Ruff 0.17.0, mypy 2.4.0, build 1.6.1, PyInstaller 6.22.3, setuptools 84.0.0, wheel 0.48.0 |

Original root: `I:\CODEX-API-ENGINE`. Work/cache directories: `.venv`, `.tmp`,
`.cache/client-deps`, `.cache/dotnet`, `.cache/nuget`, `.cache/npm`, `.cache/electron`.
They are ignored and not recovery inputs. Existing global toolchains are used,
not silently replaced. Exact tool versions are an observed environment, not a
guarantee that arbitrary newer dependencies reproduce identical binaries.

Previous cleanup, recorded in b379795: .NET first use added a repository-local tools
directory to persistent user PATH; only that task-created entry was removed, with
other entries preserved. Future scripts must set
`DOTNET_ADD_GLOBAL_TOOLS_TO_PATH=false`, `DOTNET_GENERATE_ASPNET_CERTIFICATE=false`
and repository-local DOTNET_CLI_HOME before build commands. The build script does so.
Do not change unrelated PATH entries. The earlier Electron cache side effect was
confined back to the repository; its installer uses lowercase `electron_config_cache`.

The read-only resume script does not initialize runtimes, install dependencies,
modify PATH, change credentials or start a broker. Rebuilding is an explicit
separate action. Production broker/config/vault are not part of fresh recovery.
