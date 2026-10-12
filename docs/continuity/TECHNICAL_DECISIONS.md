# Decisions to preserve

## M4 current checkpoint

M4 extends existing GUI and ApplicationRegistry; no new admin IPC. Selection pins server/pipe/runtime, restores offline, rechecks before operations. Remember uses exclusive create and never overwrites unknown files. Portable descriptor is ignored. No automatic provider probes or granting authority. Local candidate is explicitly blocked pending publication gates.


## M3 decisions

Reuse the compatible adapter for llama.cpp; exact model IDs are opaque, with no
filesystem authority. Do not widen to arbitrary Unicode/spaces. Reject incomplete
declared HTTP lengths even when bytes parse. Real Qwen is read-only; faults use
disposable subprocess endpoints. Client timeout is not cancellation. Dev5 artifacts
are separate; no production migration.


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
  proofs. Preserve legacy JSONL reads and protocol v1 framing. Retention is opt-in and implemented by M1; do not silently migrate or rotate
  production audit data.

Authoritative details: [architecture](../../ARCHITECTURE.md),
[protocol](../BROKER_PROTOCOL.md), [registry](../APPLICATION_REGISTRY.md),
[SDK contracts](../CLIENT_SDKS.md), [security](../../SECURITY.md).


## M2 decisions

- Extend AccessRuntime and the existing protocol, not a parallel execution/quota engine.
- Route only exact operator-declared model IDs and implemented chat/embedding adapters.
- Keep legacy explicit-provider grants compatible; new routing is separately opt-in.
- Cloud/fallback require operator permission. Never substitute after dispatch.
- Availability is bounded, application-scoped, recent observation, not a paid probe.
- Unknown usage remains null; provider reporting is not final billing confirmation.
- Preserve generic SDK requests; add engine BrokerClient helpers without changing
  existing client-package convenience method meanings or requiring upgrades.
- No trusted instruction hierarchy, moderation or cancellation is fabricated for POK.
See [the contract](../CAPABILITY_ROUTING.md).
