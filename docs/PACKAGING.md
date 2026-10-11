# Windows builds and release process

Run `scripts/setup.ps1` on Windows x64 with Python 3.14. All caches and scratch files
used by project scripts live in `.tmp`, `.cache`, `.venv` and `build` in this repository.

`scripts/test.ps1` runs Ruff, strict mypy, pytest, native Windows storage tests and an
80% minimum coverage gate. Tests never use the real key or make live API calls.

`scripts/build.ps1` validates the version, builds a wheel and source archive, then
inspects their members. `-Executable` adds a windowed one-file PyInstaller build of
`gui/launcher.py`. It uses no `--add-data` repository glob. Only imports are bundled.

`scripts/check_artifacts.py` rejects secret file names, inspects decompressed wheel
and source members, checks executable archive entries, and compares payload bytes
against the retained key in memory when it exists. Output is pass/fail only. This is
a defense-in-depth check, not a claim to detect arbitrary transformed secrets.

`scripts/release.ps1` runs validation and both builds, then writes SHA-256 artifact
hashes to `dist/SHA256SUMS.json`. It never publishes or commits. Check the artifacts
in a clean Windows VM before distribution. Code signing and installer creation are
future release engineering work, not present security guarantees.

The source archive intentionally contains the runtime package and required metadata;
the complete source repository additionally supplies tests, examples, scripts and docs.
Build inputs are currently version-bounded, not fully locked; byte-for-byte reproducible
builds and dependency attestations are roadmap items.

CI is `.github/workflows/ci.yml`: Windows/Python 3.14, tests, builds, archive checks and
artifact upload. Workflow credentials have read-only repository permissions. CI has
no API key and performs no live authentication check.
