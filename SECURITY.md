# CAE security model

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
