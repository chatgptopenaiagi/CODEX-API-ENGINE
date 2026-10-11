# Repository maintenance instructions

This repository implements CODEX API ENGINE v0.2.0. Read ARCHITECTURE.md and SECURITY.md
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

Use scripts/setup.ps1, scripts/test.ps1 and scripts/build.ps1 -Executable. Keep
temporary files and caches in the repository. Do not use real credentials in tests.
Do not log arbitrary exception messages or enable HTTP wire debugging. Error codes
and metadata are sufficient. Preserve the default-deny, fixed-origin design.

No network broker/service, authenticated application identity, package publication,
code signing or Windows 11 certification is implied by an in-process smoke test.
Record the platform and exact checks actually performed in docs/VALIDATION.md.
