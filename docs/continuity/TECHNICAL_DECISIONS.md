# Decisions to preserve

## Managed audit storage decisions

Opt in explicitly to a fresh private store; never automatically migrate legacy
production logs. Use JSONL plus bounded ownership/intent metadata, existing Windows
file locking and non-overwriting rename; no database/service/cloud dependency.
Manifest ownership limits deletion scope. Successful writes flush; no power-loss
or hostile same-user guarantees. See [the full contract](../validation/AUDIT-M1-RETENTION-ROTATION.md).

- Extend the independent named-pipe broker, not a second service or replacement IPC
  protocol. Protocol v1 and existing Python SDK remain compatibility contracts.
- Kernel-derived peer SID/PID/image and enrollment authenticate executable identity;
  a client-supplied application name never grants access. Interpreters and loaded
  code remain a same-user limitation, not a solved isolation boundary.
- Provider credentials stay in the Windows vault behind abstractions. No production
  migration, credential export endpoint or environment-key dependency is introduced.
- Policies default deny; enforce model/provider restrictions and reserve persistent
  day/minute quotas before vault/provider I/O. Concurrency limits are per runtime.
- Registry commands authenticate an existing operator enrollment; no untrusted
  client administrative endpoint. Preserve DACLs and fail-closed file recovery.
- No automatic replay of possibly billable generation. Reconnect on the next request.
- Explicit connection descriptor / `CAE_CONNECTION_FILE`, rather than fabricated
  automatic discovery. Node uses in-process native bindings, preserving caller PID.
- Keep development versions/artifacts separate. Preserve history and historical
  releases; source checkpoint publication does not authorize a downloadable release.
- Keep the security increment in a draft PR/development branch until unfinished work
  and required checks support promotion. The original checkpoint introduced no
  features; subsequent development is explicitly recorded in milestone reports.
- Audit IDs are broker-generated ContextVar metadata, not wire IDs or authorization
  proofs. Preserve legacy JSONL reads and protocol v1 framing. Retention is separate
  unfinished work; do not silently migrate or rotate production audit data.

Authoritative details: [architecture](../../ARCHITECTURE.md),
[protocol](../BROKER_PROTOCOL.md), [registry](../APPLICATION_REGISTRY.md),
[SDK contracts](../CLIENT_SDKS.md), [security](../../SECURITY.md).
