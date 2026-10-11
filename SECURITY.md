# CAE security model

## v0.3.1 independent-process boundary

The independent broker verifies the client PID using Windows named-pipe APIs, opens
that process to obtain its token user SID and image path, and hashes the enrolled
image. Application names in requests are rejected. Both image path and SHA-256 must
match an administrator enrollment; the SID must match the broker account. Clients
also verify the server SID, image path and hash before sending a request.

The pipe uses a protected DACL granting only the broker user and SYSTEM, remote-client
rejection, non-inheritable handles and first-instance exclusivity at startup. Client
handles use SECURITY_IDENTIFICATION so a malicious server cannot impersonate them
at impersonation level. Provider keys never cross IPC; no credential mutation/export
endpoint exists. Administrator shutdown requires a separate enrollment flag. Policy,
model/profile restrictions, quota and audit execute in the broker before key retrieval.

Limits: this is same-account process separation, not hostile same-account isolation.
That account can access its Windows vault, modify writable configuration or images,
inject/debug permitted processes, create pipe instances or deny service. Hashing the
on-disk image is not code signing, a measurement of loaded memory, or proof of scripts
and plugins. Enrolling Python authorizes every script using that executable. The
enrollment helper deliberately grants the operator's interpreter admin permissions;
do not expose that interpreter to untrusted code. There is no separate service account,
session-ID restriction, AppContainer boundary or installer-managed file ACL.

Eight workers and message/time limits bound ordinary resource use, not malicious
same-account denial of service. Disconnecting a client does not undo an accepted
provider request or restore quota. No automatic replay occurs. Shutdown drains
in-flight requests; it does not kill unrelated processes. See
[protocol](docs/BROKER_PROTOCOL.md) and [executed security checks](docs/BROKER_VALIDATION.md).

## Retained v0.3.0 / v0.2.0 in-process interfaces

v0.3.0 adds provider-specific credential namespaces, strict explicit TOML configuration,
capability/model policies, durable atomic daily quotas and schema-constrained audit.
See [policy/audit boundaries](docs/POLICY_AUDIT.md) and [provider boundaries](docs/PROVIDERS.md).
Cloud origins remain restricted; local services accept only literal loopback addresses.
The existing OpenAI credential target is unchanged. These controls remain within a
trusted-host boundary; they do not authenticate hostile application processes.

## Boundaries

Windows Credential Manager protects stored credentials for the current Windows
account. CAE has no plaintext, environment-variable or Codex-auth fallback.
Applications use the SDK's operation-based broker instead of retrieving keys.

An in-process broker cannot stop malicious Python code in the same process from
accessing internal objects, nor prevent another process running as the same Windows
account from calling Win32 credential APIs. Application names are host-supplied
policy labels, not authenticated identities. v0.2.0 is for trusted applications.
Separate-identity service isolation and authenticated named pipes are roadmap work.

## Implemented controls

- Explicit grants bind an application, profile and operation. Denial happens before
  credential access. No export operation exists in the SDK or credential manager.
- Lowercase profile identifiers exclude path separators and ambiguous target names.
- Key syntax is checked locally; only an authenticated API result establishes validity.
- Writes are verified by constant-time comparison with a readback.
- TLS certificate and hostname verification are mandatory. Only official model-list
  and Responses endpoints can be called. Redirects and environment proxies are not used.
- API errors discard provider bodies and transport exception text. Diagnostic fields
  are fixed metadata. Response data is recursively redacted for key patterns,
  sensitive fields and exact credential echoes.
- Native credential buffers are zeroed before release. Python strings, HTTP internals,
  paging and crash dumps cannot be reliably erased by Python; no full-memory-erasure
  guarantee is made. Do not enable traceback-local capture or HTTP wire debugging.
- `CredDeleteW` removes the stored credential. This is logical deletion, not proof of
  physical erasure from disks, backups, snapshots or pagefiles.
- Local rotation replaces the stored key. Revoking the old key in OpenAI remains
  the account administrator's responsibility. CAE never creates or revokes keys itself.
- The test suite uses synthetic keys and isolated temporary Windows credential targets.
  CI never reads production credentials and performs no real API requests.

## Source secret handling

`apy_key.txt` is an explicitly retained, user-owned input. Do not delete, move,
rename, overwrite or modify it. Do not ask again about deletion. It is ignored by
Git and excluded from source/wheel/executable packages. Import reads it into memory
only. Never print, hash for display, commit, upload or include its contents in reports.
Ordinary future provisioning should use the hidden CLI prompt or masked GUI.

## Review and reporting

Report suspected vulnerabilities privately to the repository owner through an
agreed private channel; no public security mailbox has been established. Include
reproduction steps using synthetic credentials only. If a real key is exposed,
revoke it through OpenAI and provision a replacement; deleting a log is insufficient.

Before release: verify tests, type checks, package exclusions, metadata-only error
paths and a Windows native storage roundtrip. Signing and external penetration
testing have not been performed. Unsigned local builds are not enterprise-certified.
