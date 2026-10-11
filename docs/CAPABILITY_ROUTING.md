# Capability routing — M2 implementation contract

Development implementation: 0.5.0.dev4. Executed acceptance and limits are recorded
in [ROUTING-M2](validation/ROUTING-M2.md). No live-provider compatibility is implied.

The existing authenticated broker and AccessRuntime remain authoritative. Protocol
v1 framing is unchanged. New `capabilities` and `route` operations are opt-in.
Legacy operations keep their policy semantics. No production configuration migrates.

## Threat boundary and decisions

Unenrolled/revoked processes are rejected by existing OS peer authentication.
Enrolled callers cannot supply identities, endpoints, profiles, credentials or policy.
An exact request schema and bounded text reject privilege-bearing metadata. Routing
requires explicit operator grants intersected with existing deny-overrides operation,
provider and model rules. Missing routing grants deny; cloud requires affirmative
permission. Models are exact names, without aliases or wildcard route declarations.

Local adapters use validated literal IPv4/IPv6 loopback endpoints, no environment
proxy and no redirects. This constrains CAE transport, not a local server's subsequent
network access. Same-account hostile code and operator configuration tampering remain
outside the established isolation boundary. Provider bodies and failures are untrusted.
No prompt, response or raw exception enters audit metadata.

## Versioned bounded contract

Contract version 1 declares only `chat_generation` (single untrusted user text) and
`embeddings`, matching existing adapter implementations. Moderation, privileged
instructions, structured output, streaming and cancellation are unsupported.
Requests name one exact model, input and mode: EXPLICIT_PROVIDER, LOCAL_ONLY,
LOCAL_FIRST or CLOUD_ONLY. Explicit mode requires a provider. `allow_fallback` defaults
false and requires operator permission. LOCAL_ONLY can never select cloud.

Selection sorts eligible providers by local preference, configured priority and
provider ID. Operator-disabled providers and short-lived, application-scoped observed
failures are ineligible. Unknown availability is not proof of health; no paid probes
or model discovery is performed implicitly. Cloud selection after unavailable local
candidates requires request AND operator fallback permission. No provider operation
is retried after dispatch, including timeout and malformed response. These outcomes
remain uncertain; no replacement request is sent.

Existing per-provider rule quotas/concurrency apply at dispatch, including conservative
consumption on failure. They are not a monetary budget or an application-wide quota.
Switching routes cannot bypass a selected provider's limits; different explicitly
allocated provider rules retain their independent budgets. Audit admission precedes
vault access. Routing policy changes require restart; enrollment revocation retains
next-connection semantics. No already accepted operation is cancelled.


## Operator configuration

Extend an existing trusted runtime TOML; restart only the broker whose configuration
the operator deliberately changed. No default grant, endpoint discovery or migration.

```toml
schema_version = 1
[[providers]]
name = "local"
kind = "ollama"
authenticated = false
routing_models = ["operator-approved-model"]
routing_priority = 100
routing_enabled = true

[[rules]]
id = "application-local"
app = "sample-app"
provider = "local"
profile = "default"
operations = ["chat"]
models = ["operator-approved-model"]
routing_modes = ["LOCAL_ONLY", "LOCAL_FIRST", "EXPLICIT_PROVIDER"]
allow_cloud = false
allow_fallback = false
max_requests_per_day = 100
max_requests_per_minute = 10
max_concurrent_requests = 2
```

Provider defaults: zero routing models (not routeable), priority 100 (0–10000),
enabled true. At most 128 unique exact model IDs per provider; no wildcard/aliases.
Rule defaults: no routing modes, cloud false, fallback false. Configuration size
remains bounded at 128,000 characters. Registry authorization edits preserve these
operator fields; the CLI does not expose new routing-policy editing flags.
Legacy `chat`/`embeddings` grants keep their existing explicit-provider permissions.
Routing restrictions govern new `route` operations, not a retroactive restriction on
separately authorized legacy calls. Remove legacy cloud grants if all cloud access
must be prohibited. Deny rules remain authoritative for both interfaces.

## Request and response

The protocol v1 envelope remains unchanged; `args` for operation `route` is:

```json
{"contract_version":1,"capability":"chat_generation","model":"operator-approved-model",
 "input":"A bounded user question","routing_mode":"LOCAL_ONLY"}
```

Only these required fields and `provider`, `allow_fallback`, `max_tokens` are accepted.
Version is integer 1, input is a UTF-8 string of 1–8192 characters, model matches the
existing 128-character model grammar, max_tokens is integer 1–4096 (default 256).
Provider is permitted and required only for EXPLICIT_PROVIDER. Fallback is a boolean
(default false), allowed only with LOCAL_FIRST. False means no cloud substitution;
all modes also prohibit replacement after dispatch. A fallback-enabled request
requires `allow_fallback=true` in every applicable routing grant for each candidate.
Cloud also requires `allow_cloud=true`; a client preference never grants permission.

Selection: validate request, intersect configured adapter capability/model with
existing allow/deny rules and opt-in mode grants, constrain locality/provider, sort
by locality preference then numeric priority then provider ID, omit disabled/recently
failed candidates, select first. No candidate is a fixed denial/unavailable error;
no quota is reserved and no vault read occurs. The selected operation uses the
existing runtime's concurrency slot, persistent day/minute reservations and required
audit admission. Each accepted dispatch consumes quota even if it later fails.
Quota/capacity denial never triggers another candidate. There is no extra probe.

Response fields are contract_version, capability, provider_id, model_id, result,
usage, completion_status and routing_metadata. Text result is nonempty and at most
8192 characters; embeddings are one finite numeric vector with 1–4096 dimensions.
Normalized output is bounded to 48,000 serialized bytes before the broker's existing
frame limit. Extra adapter fields are discarded. Provider model IDs, when returned,
must equal the requested ID; implicit provider aliases may therefore be rejected.
An explicit incomplete provider status is rejected. COMPLETED means a validated
result was returned, not proof of a provider stop reason or final invoice.
`provider_finish_reason` remains UNKNOWN. Usage CONFIRMED_USAGE means valid
provider-reported token fields; it is not independent billing confirmation.
Missing/partial usage is UNKNOWN_USAGE with null counts, never fabricated zero.
Embedding output-token usage is null. Estimated monetary accounting is unsupported.

## Discovery, availability and failure state

`capabilities` takes empty args and returns versioned contracts and only authorized
provider/model declarations; up to 64 declarations plus a truncation flag. It exposes
no endpoint, credential reference or private profile. Contract metadata specifies
fields, bounds, usage, instruction and cancellation limitations. Discoverable does
not mean reachable. Configured declarations have UNKNOWN availability until observed.
Success gives AVAILABLE for five monotonic seconds; an ambiguous adapter failure
marks that app/provider/model UNAVAILABLE for five seconds. Disabled providers remain
UNAVAILABLE. Caches are process-local, bounded to 1024 entries each, expire from
selection and never grant authority; restart clears them. Eviction is conservative
about authorization but can permit a new independent request to try again.
No claim of model availability exists before a successful model operation. No network
scan, automatic model-list request, paid probe or indefinite health cache is used.

NOT_DISPATCHED selection metadata precedes runtime execution. Credential, quota,
concurrency and required-audit failures retain their established fixed errors.
Once adapter execution starts, transport timeout, malformed output, or ambiguous
failure returns request_outcome_unknown and never retries within that request.
A later independent request can select an authorized fallback after observed local
failure. Applications must not automatically resubmit unknown-outcome requests.
Audit failure after provider completion remains ambiguous even if its error is
`audit_unavailable`. Client disconnection does not cancel accepted provider work.

New errors: capability_unknown, routing_policy_denied, provider_unavailable,
request_outcome_unknown; validation uses invalid_configuration. Raw backend errors
are never returned. Existing native 0.4 SDKs safely map unfamiliar error codes to
broker_request_failed. Updated engine BrokerClient recognizes routing errors.

## Adapter declarations and compatibility

| Adapter | Routed implemented operations | Locality | Validation scope |
|---|---|---|---|
| OpenAI, Azure OpenAI, Gemini | Single-user chat, embeddings | Cloud | Mock adapter contracts |
| Anthropic | Single-user chat only | Cloud | Mock adapter contracts |
| Ollama, vLLM, LM Studio | Single-user chat, embeddings | Literal loopback | Mock adapter contracts / mock HTTP acceptance |

Runtime declarations intersect actual adapter operations, exact configured models
and authorization. A model name in configuration is not proof it supports an operation.
Moderation, privileged role messages, reliable structured output, tools, audio,
vision, streaming and cancellation are not advertised. Trusted instructions cannot
be safely emulated by concatenation into user text. POK integration is NOT_TESTED;
see [the compatibility analysis](integrations/POK_COMPATIBILITY.md).

All five installed language SDKs have a documented generic request interface. For
Python (existing cae_client 0.4):

```python
from cae_client import CAEClient
client = CAEClient()  # Explicit trusted descriptor / CAE_CONNECTION_FILE
contracts = client.request("capabilities")
result = client.request("route", contract_version=1, capability="chat_generation",
                        model="operator-approved-model", input="Explain this text",
                        routing_mode="LOCAL_ONLY")
```

Equivalent generic calls: C# RequestAsync, C++ request, Node/Electron request,
PowerShell Invoke-CAERequest. Existing `capabilities()` convenience methods still
mean legacy provider listing; use the new operation explicitly. The engine's
BrokerClient adds capabilities() and route(). Old brokers reject new operations;
status version/capability discovery can establish support. Old operations and v1
framing are retained. No SDK silently retries generation.

## Security and limits

Routing audit adds allowlisted capability/mode/model/outcome/fallback metadata using
M1 correlation and bounded storage. No prompt/response, arbitrary metadata or raw
exception is recorded. Audit IDs carry no authentication authority. Local-only never
selects a cloud adapter; a loopback server may itself forward traffic, so complete
offline enforcement requires OS/network controls outside M2. Executable hashes do
not attest loaded scripts/modules. User-account isolation, Windows 11 acceptance,
signing, live local/cloud inference and long-running reliability remain separate.
