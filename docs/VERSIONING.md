# Versioning policy

Distribution name: `codex-api-engine`. Import name: `cae`. Development version: `0.5.0.dev4`.
Published foundation: `0.3.1`; `0.2.0` remains preserved. See [migration](MIGRATION_0.3.md) for schema/API evolution.
`pyproject.toml` and `src/cae/version.py` must match; build scripts enforce this.

Before 1.0, minor versions may introduce documented API changes. Patch versions
preserve the documented `CAE` methods and diagnostic schema. Breaking changes must
include migration notes and tests. Internal underscore-prefixed state and Win32
bindings are not public application APIs.

Status reports carry their own integer schema version. Consumers should ignore
unknown fields and handle unknown future state values conservatively. Removing or
changing field meanings requires a new schema version.

The v0.2 public surface is `CAE`, `CAEError`, `__version__`, explicit trusted-host
`Broker`/`Grant` composition, `CredentialManager` administration and `HealthMonitor`.
No stability promise is made for raw provider response schemas beyond sanitation.
