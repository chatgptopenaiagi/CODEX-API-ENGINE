# Repository maintenance instructions

This repository develops CODEX ACCESS ENGINE v0.5.0.dev1, with validated 0.4.0 client
SDKs, and preserves published v0.2.0/v0.3.1.
Read ARCHITECTURE.md, docs/ACCESS_ENGINE.md and SECURITY.md
before changing trust boundaries. Runtime code belongs in src/cae; root component
folders document ownership rather than duplicate implementations.

## User-owned credential input

The user explicitly requires `I:\CODEX-API-ENGINE\apy_key.txt` to remain unchanged.
Never delete, move, rename, overwrite or modify it. Never ask again about deletion.
Never print its contents or include it in logs, Git, source archives, wheels or EXEs.
Do not inspect it during ordinary repository exploration. The import helper and
artifact checker may read it in memory without exposing contents. It was imported
and authenticated successfully; do not reimport or repeat live calls unnecessarily.

Do not access or alter Codex authentication. Do not write outside this repository,
except to the CAE Windows Credential Manager targets needed for authorized work.
Tests use unique synthetic targets and clean up only those targets.

## Validation

Use scripts/setup.ps1, scripts/build.ps1 -Executable, scripts/build_clients.ps1,
then scripts/test.ps1 (full validation includes native executable tests). Keep
temporary files and caches in the repository. Do not use real credentials in tests.
Do not log arbitrary exception messages or enable HTTP wire debugging. Error codes
and metadata are sufficient. Preserve the default-deny, fixed-origin design.

The independent broker has a local named-pipe process boundary and executable
enrollment. This does not imply separate-account isolation, code signing, public
publication or Windows 11 certification. See docs/BROKER_PROTOCOL.md.
Record the platform and exact checks actually performed in docs/VALIDATION.md.
