# CODEX ACCESS ENGINE (CAE) v0.3.1 — Independent Windows Broker

This is CAE's initial independent-broker release. CAE is a reusable AI connectivity,
credential and policy engine, not an AI agent.

- CAE-Broker.exe runs separately from Codex CLI, Control Center and consuming apps.
- Local Windows named pipes use explicit permissions, OS-derived executable enrollment,
  client/server identity checks, bounded messages and concurrent connections.
- Existing policy, quotas, audit, provider routing and credential access run centrally.
- BrokerClient provides the installed public IPC SDK without returning provider keys.
- CLI supports broker start, stop, restart, status, health and diagnostics.
- Independent console and desktop client EXEs demonstrate shared-broker operation.
- Existing in-process SDK compatibility, Control Center and seven providers are preserved.

## Included assets

CAE-Broker.exe, CAE-Console-Client.exe, CAE-Desktop-Client.exe,
CAE-Control-Center.exe, codex_api_engine-0.3.1-py3-none-any.whl,
codex_api_engine-0.3.1.tar.gz and SHA256SUMS.json.

These are the existing tested artifacts built from source commit
`04a12c1eadc5d7e5a2e0eda9b99a648fae48e3b1`; they were not rebuilt for publication.
The release source adds publication documentation. Packaged runtime code matches
the release implementation; packaged documentation retains its original build snapshot.
Use the tagged repository for current installation/enrollment instructions and complete
tests and build scripts. Verify downloads against SHA256SUMS.json.

## Validation

Publication revalidation passed 153 tests with 92.37% statement coverage, Ruff and
strict mypy. Both external applications used one broker; terminating the console
left the desktop functional. Shutdown, restart and forced-crash recovery passed.
Publication checks use no paid generation and do not modify production credentials.

## Security and compatibility limits

Builds are unsigned. The broker runs under the current account; it is not a
separate-identity Windows service or a hostile same-account security boundary.
Enrolled interpreters authorize all scripts they run. Executable hashes do not attest
loaded process integrity. No code signing or independent penetration certification is
claimed. Local validation used Windows x64 build 19045 and Python 3.14.7; Windows 11
certification remains pending. New provider integrations retain mock-contract testing.

The original v0.2.0 release, credentials and Codex authentication remain unchanged.
See the repository's BROKER_PROTOCOL.md, BROKER_VALIDATION.md and
INTEGRATION_RESULTS.md under docs/ for protocol, limitations and executed evidence.
