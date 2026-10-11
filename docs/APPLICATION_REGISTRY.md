# Application administration — 0.5.0.dev1

Install the development wheel to use the administrative CLI. The published v0.3.1
broker is preserved and is not silently upgraded. Choose a separate development
configuration and start the development broker explicitly when testing new behavior.

## Operator commands

All commands require an explicit broker configuration and an existing **admin**
enrollment for the command's real executable. Enrolling Python as admin authorizes
every script using that interpreter; this is not script-level isolation. Commands
do not read or modify provider credentials and are not available through client IPC.

```powershell
cae apps list --broker-config .cae/development/broker.json
cae apps register --broker-config .cae/development/broker.json --id my-app --image C:\Apps\MyApp.exe
cae apps inspect --broker-config .cae/development/broker.json --id my-app
cae apps authorize --broker-config .cae/development/broker.json --id my-app --provider openai --operations models health diagnostics --max-requests-per-day 100 --max-requests-per-minute 10 --max-concurrent-requests 2
cae apps revoke --broker-config .cae/development/broker.json --id my-app
```

The application image and broker configuration must actually exist. Use the existing
enrollment helper to create a separate configuration first; it refuses overwrites.
An operator must register the executable, authorize it, and restart to load changed
provider policy. Applications receive only the non-secret connection descriptor.

Registration records the app ID, image/hash, current operator principal SID,
registration timestamp and revocation metadata. Inspection adds the app's configured
rules, including provider/model restrictions and limits. Legacy enrollments have
no invented registration timestamp. Registration grants no provider capabilities;
status remains available to an enrolled client. Revoked IDs cannot be registered
again through this API, preventing accidental reactivation of retained grants.

`authorize` replaces the selected app/provider/profile/effect rule while preserving
other apps and the existing quota ID. Use `--deny` for an explicit deny rule; deny
continues to override allow. Chat/embeddings require `--models` with an explicit
approved model list. Unknown operations, providers, profiles and invalid limits fail
before configuration replacement. Existing administrator enrollments cannot be
revoked or assigned application rules by this interface.

## Effective time and revocation

The development broker re-reads enrollment at each new request. The wire protocol
serves one request per connection, so removal prevents subsequent connections from
performing protected actions without restarting that broker. Requests already
authenticated/in flight may finish; cancellation/rollback is not claimed.

The CLI checks the broker's authenticated `enrollment_reload` status flag. Revocation
returns `effective: next_connection` only when supported; an old, unavailable or
unverifiable broker returns `effective: broker_restart`. **v0.3.1 caches enrollment
and requires a restart.** Policy changes always report `effective: broker_restart`.
The CLI never silently stops the operator's broker or changes its production state.

## Rate and concurrency rules

Optional TOML fields: `max_requests_per_minute` and `max_concurrent_requests`, positive
integers. Omission preserves earlier unlimited minute/concurrency behavior; existing
daily quota fields remain compatible. The broker's global eight-connection bound
continues to apply independently.

Daily and fixed UTC-minute counts reserve together in one SQLite transaction before
vault/provider access. Failed provider calls count; policy/rate/concurrency denials
do not call the provider. Counters survive restart. All matching limits must permit
the operation. A fixed-minute window can allow bursts at a boundary; this is not a
sliding-window or billing-budget implementation. The Windows clock remains trusted.

Concurrent slots apply to provider operations within one broker runtime, release on
success or exception, and remain occupied while accepted provider work is running
even if the client disconnects. Separate broker instances do not share concurrency
slots; they can share transactional quota counts if explicitly configured to do so.
Offline status/diagnostic reads do not consume provider-operation limits.

## Failure and storage behavior

Edits use a bounded Windows byte-range lock and flushed temporary files.
`ReplaceFileW` preserves the original file DACL; no ACL merge errors are ignored.
Requested and completed changes produce fixed metadata audit events, without prompts
or credentials. Registration metadata cannot itself grant a permission. Revocation
removes enrollment before updating its history record, so an interrupted metadata
update cannot restore access. An audit/filesystem failure can require operator
inspection to determine whether an edit committed.

If filesystem recovery fails, `.cae-edit-*` recovery files are retained instead of
discarding the original configuration. They and `*.apps.json`/`*.apps.lock` are private
local state and Git-ignored. Keep all configuration in a protected `.cae/` directory.
Manual edits outside the registry lock, hostile same-user code, loaded-code integrity,
service identity separation and installer-managed ACLs remain outside this guarantee.

Audit enrichment/rotation and stronger installation/service controls remain unfinished.
See [validation](validation/SECURITY-0.5.0-dev1.md) and
[Microsoft ReplaceFileW semantics](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew).
