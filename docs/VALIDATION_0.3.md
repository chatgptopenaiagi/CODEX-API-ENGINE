# CODEX ACCESS ENGINE v0.3.0 validation

Validated locally on 2026-10-11 with Python 3.14.7 and Windows x64 build 19045.
Development branch: `feat/codex-access-engine`. No new GitHub release was published.

- 118 tests passed, with 92.43% runtime statement coverage and no test warnings.
- Ruff passed; strict mypy passed for all 19 production Python modules.
- Mocked wire-contract tests cover OpenAI, Azure OpenAI, Anthropic, Gemini, Ollama,
  vLLM and LM Studio model/chat/embedding behavior, including unsupported operations.
- Security tests cover origin rejection, token-in-header routing, deny precedence,
  model restrictions, deny-before-credential-access, exception sanitation, metadata
  audit privacy, audit failure, SQLite quota concurrency and restart persistence.
- A real loopback HTTP server validated independent local-provider transport and
  confirmed no credential access or Authorization header for unauthenticated local use.
- Legacy v0.2 Broker/SDK tests and isolated Windows vault roundtrips still pass.
- Control Center tests cover tabs, masking, key clearing, asynchronous results and
  validated configuration loading/applying. EXE `--self-test` passed.
- Wheel, source archive and `CAE-Control-Center.exe` built in `dist/0.3.0/`.
  Checksums, archive exclusions and packaged-runtime/source matching passed.
- The new wheel installed into an isolated repository-local virtual environment.
  One authenticated model-list GET through its new capability runtime confirmed
  OpenAI authentication valid, API available, broker ready and policy ready.
- CLI configuration diagnostics ran offline and reported unknown network health
  rather than silently probing or claiming cached connectivity.
- All four original v0.2.0 release files retain their previously verified SHA-256 hashes.

The retained `apy_key.txt` and existing production credentials were not changed.
No new provider key was provisioned, and no live generation or embedding call was made.

Limits: provider contracts other than the OpenAI model-list probe are mock-tested,
not live-certified. The broker still trusts its hosting process and Windows account.
The EXE is unsigned; dedicated Windows 11 acceptance and separate-identity IPC are
pending. The updated GitHub workflows were prepared locally, not executed remotely
for this development branch. The previously published v0.2.0 CI record is separate.
