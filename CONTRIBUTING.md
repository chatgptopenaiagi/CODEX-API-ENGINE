# Contributing

Use Windows 11 x64 and Python 3.14. Run `scripts/setup.ps1`, then
`scripts/test.ps1`. Keep tooling caches and temporary files inside the repository.

Never read or print `apy_key.txt` during routine inspection. It must remain unchanged
and ignored. Use synthetic credentials in tests. Windows integration tests create
unique `test-<uuid>` profiles and delete only those profiles in `finally` blocks.

Changes to storage, transport or policy require negative tests showing fail-closed
behavior and sanitized errors. Do not expose a get-key/export method on `CAE`.
Do not introduce wildcard build data inclusion, arbitrary API origins or redirects.

Run formatting, lint, strict typing and tests before release. `scripts/release.ps1`
builds and inspects artifacts locally; publication and signing are separate actions.
Document intentional limitations rather than claiming production security guarantees
that tests do not establish. Update CHANGELOG and both version sources together.
