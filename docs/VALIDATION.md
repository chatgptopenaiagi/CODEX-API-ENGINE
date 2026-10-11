# v0.2.0 validation record

Date: 2026-10-11. Execution platform: Windows x64 build 19045 (Windows 10),
Python 3.14.7. The requested primary target remains Windows 11 x64; a separate
Windows 11 acceptance run has not been performed in this environment.

## Credential integration

| Check | Result |
|---|---|
| Credential import | SUCCESS |
| Windows Credential Manager write/readback | SUCCESS |
| OpenAI authentication | SUCCESS |
| API connectivity | SUCCESS |
| CAE broker | Ready, in-process |

One authenticated `GET /v1/models` request was used. No generation request was made.
The input file remains unchanged at the user's explicit instruction. No credentials,
provider bodies or credential-derived hashes are included in this record.

## Local verification

- 68 tests passed, including an isolated native Windows Credential Manager roundtrip.
- Runtime statement coverage: 94.77%; configured minimum: 80%.
- Ruff checks passed. Strict mypy passed for all 12 runtime Python modules.
- Tk console smoke verified masking, entry clearing and asynchronous UI result delivery.
- Source archive and wheel built successfully; wheel installed and imported in a fresh
  repository-local virtual environment. Installed `cae --version` returned 0.2.0.
- Windows standalone EXE built successfully. Hidden `--self-test` created and destroyed
  the UI without reading credentials or contacting the API; process exited 0.
- Distribution inspection checks archive members and payloads for forbidden source
  secret files and the exact retained secret, without printing either. Checks passed.
- Git ignore verification confirms `apy_key.txt` is excluded.

## Limits

No CI runner execution, Windows 11-specific acceptance, code signing, external
security audit or package publication was performed. Responses API behavior is
tested with synthetic transports; no paid generation was performed. In-process
policy does not isolate hostile same-user applications. The validation record is
evidence for this local build, not a claim of enterprise certification.
