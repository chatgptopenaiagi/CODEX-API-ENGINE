# Troubleshooting and FAQ

**`credential_missing` / not configured:** provision with the human console under
the same Windows account used by the application. Verify the selected profile.

**Credential operation failed:** check that Windows Credential Manager is available
in an interactive user session. CAE never falls back to a plaintext file. A profile
already present requires Replace rather than Add.

**Authentication invalid:** replace an expired/revoked/incorrect key, then probe again.
**Permission denied:** the key/project may lack model-list permission. A restricted
key can be valid yet fail this particular probe; do not treat a 403 as malformed key.
**Rate limit:** wait before retrying and review account limits. **Unavailable:** check
DNS, system trust store and access to `api.openai.com:443`. CAE does not honor proxy
environment variables or custom API base URLs.

**Can I use Codex login or a ChatGPT subscription?** No. They are independent of
OpenAI API authentication, permissions and billing. CAE leaves Codex state untouched.

**Does the probe generate tokens?** It performs one authenticated model-list GET,
not a generation call. No POST or streaming session is opened by connection tests.

**Does the SDK return the key?** No. Store backends are trusted infrastructure and
can read credentials internally. Application methods only return sanitized results.

**Is the broker a service?** No, it is an in-process policy layer for trusted hosts.
There is no IPC server, port, service installation or authenticated external identity.

**Does deleting a stored key revoke it?** No. Revoke in OpenAI separately. Deletion
removes the Windows vault entry, not all historical copies or backups.

**Can I use CAE on Linux?** The transport and policy tests are portable; the default
secure storage intentionally requires Windows. No cross-platform plaintext fallback.

**Why are errors terse?** Provider error bodies and arbitrary exception strings can
contain credentials. Use the fixed classification, HTTP status (where available) and
UTC probe time to investigate without enabling secret-bearing logs.
