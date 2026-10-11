# Policy, quotas and audit

Policies are explicit, human-readable TOML (`examples/access.toml`). Unknown fields,
unknown operations, malformed identifiers, unsupported origins and secret-like key
content are rejected. `schema_version = 1` is required. Empty rule sets deny all.

Each rule binds a stable ID, app, provider alias, profile, operation set, effect,
optional model set and `max_requests_per_day`. Chat/embedding allow rules require
explicit model names or a deliberately chosen `*`. Matching deny rules override all
allow rules. Changing provider configuration and exporting credentials are not SDK
capabilities, so no policy can grant them.

All matching allow-rule quotas apply. Counts are reserved atomically in a SQLite
transaction before credential access/network I/O. The UTC day determines reset.
Concurrent callers/processes using the same ledger cannot overrun the same rule's
limit. Allowed network attempts count even if credentials/network/provider subsequently
fail. Requests are not retried automatically in the new adapter layer. A restarted
runtime with the same configuration ledger retains its counts. Offline metadata reads
do not consume network quotas. Rule IDs must remain stable when editing policy;
renaming IDs creates new counters and is a privileged administrative operation.

Without an explicit configuration file, counters are memory-only and reset when the
runtime closes. Durable state lives in `.cae/quotas.sqlite3` and `.cae/audit.jsonl`
beside an explicit config file. These are local administrative data, not secrets, but
must be protected against untrusted modification. There is no tamper-proof or
cross-account quota claim.

Audit events contain only UUID, UTC timestamp, fixed event type, app, provider,
profile and operation. They do not contain prompt text, response text, credentials,
authorization headers, endpoints or arbitrary exception messages. Credential events
distinguish change requests from verified completion. A failed audit write before
execution prevents the request. An audit failure after a completed operation can
produce an error despite completion; callers must not blindly retry billed operations.

The in-memory view is bounded. Durable audit reads parse and validate a bounded
tail of the JSONL file. Invalid records fail with a fixed error. SDK audit views filter
to the current app; the human Control Center can inspect administrative records.
The log is append-only by CAE convention, not cryptographically tamper-evident and
not an OS-secured append-only filesystem. Hosts should rotate/archive it as needed.
