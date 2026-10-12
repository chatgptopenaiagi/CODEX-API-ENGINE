# POK compatibility investigation — PARTIAL / NOT_TESTED

Read-only inspection on 2026-10-11 of Poker-Odds-Knowledge commit
`e45856b543f21fea776985ec565cb9efc6ee2ae6`. No POK files, settings, branches or
dependencies were changed. No coach request or cloud generation was performed.

Source references: [coach contract and transport](https://github.com/chatgptopenaiagi/Poker-Odds-Knowledge/blob/e45856b543f21fea776985ec565cb9efc6ee2ae6/server/coach.ts),
[routes](https://github.com/chatgptopenaiagi/Poker-Odds-Knowledge/blob/e45856b543f21fea776985ec565cb9efc6ee2ae6/server/coach-routes.ts).
CAE contracts: [SDK](../CLIENT_SDKS.md), [protocol](../BROKER_PROTOCOL.md),
`src/cae/providers.py` and `clients/nodejs/`.

## Compatibility findings

POK separates optional coaching from deterministic education/game logic. Its
transport requires moderation and model responses with AbortSignal support and
confirmed usage. It buffers output before moderation, retains conservative budget
reservations after ambiguous failures, and has user consent and selected-context
validation. Those responsibilities must remain in POK.

| Requirement | Current CAE fit |
|---|---|
| Windows server-side Node connectivity | Implemented native Node SDK; not a browser transport |
| Broker-owned keys and authorized model access | Implemented; enrollment plus provider/model policy required |
| OpenAI generation / minimized retention | Existing adapter uses Responses with `store:false`; not equivalent to POK's full transport |
| Educational instructions | CAE text-only operation lacks a distinct trusted instructions field; concatenating instructions into user text is not equivalent |
| Input/output moderation | No moderation operation in protocol v1; incompatible with mandatory coach moderation |
| AbortSignal and cancellation | No broker/provider cancellation protocol; client timeout does not undo accepted work |
| Usage / cost | Adapter reports normalized token counts and whether usage was reported; aggregate runtime usage is not POK's persistent monetary ledger |
| Correlation | New broker-local audit correlation is not an end-to-end POK request/provenance contract |
| Local model | Adapters are mock-tested; instruction, moderation, token accounting and real inference remain NOT_TESTED |
| Failure handling | No automatic generation replay; adapters must preserve POK's uncertain-charge accounting |

## Recommended optional adapter boundary

If the missing contracts are implemented and tested, an optional Windows Node
server-side adapter could implement POK's transport interface using the installed
CAE SDK. It must stay outside deterministic mathematical code and preserve consent,
moderation, budgets, usage reconciliation and output withholding. POK's offline
edition must not require CAE. An enrolled Node image does not uniquely authenticate
all scripts/modules; document that boundary and use narrowly scoped policy.

Required extensions need version/capability negotiation: moderation, trusted
instruction separation, bounded cancellation semantics, explicit usage-confirmation
and request/provider provenance. Unknown capabilities must fail closed. Cloud access
must remain explicitly authorized; no silent cloud fallback for local workloads.
Do not implement an adapter that reports missing controls as successful.

## Proposed mock acceptance (NOT_RUN)

Test denied model/provider before communication; missing moderation fails closed;
output never displayed before moderation; absent/invalid usage retains reservation;
abort before send and after provider acceptance have distinct outcomes; no automatic
replay after ambiguous failures; offline-only never contacts cloud; prompts/results
are excluded from audit; POK works offline with CAE absent. Real local and cloud
coaching, live-money play and external live-table assistance are not integration claims.

No adapter is implemented or advertised as compatible. This is source-backed gap
analysis, not end-to-end acceptance or a replacement for POK's existing safeguards.


## M2 incremental compatibility — adapter still NOT_IMPLEMENTED / NOT_TESTED

0.5.0.dev4 supplies exact authorized provider/model routing, local-only enforcement,
explicit cloud permission, no ambiguous-dispatch replay and UNKNOWN_USAGE/null
counts when confirmation is missing. Existing Windows Node Request can invoke the
new versioned contract. Mock six-client acceptance is CAE evidence, not a POK test.
The optional adapter must remain server-side and outside POK mathematics/offline UI.

Still missing: input/output moderation, privileged instruction separation,
AbortSignal/provider cancellation and end-to-end application request provenance.
CAE request quotas remain independent per-provider allocations, not POK's monetary
reservation/reconciliation ledger. Provider-reported usage is not a billing invoice.
Retain POK consent, context validation, moderation withholding, unknown-cost handling
and its own budget limits. Do not concatenate trusted educational instructions into
CAE's single user-text field. Proposed POK acceptance above remains NOT_RUN; no
POK source was modified or a working integration advertised. No new live POK source
inspection is claimed beyond the pinned evidence above.

## M3 local inference evidence

The dev5 packaged CAE broker and console client have executed a bounded real Qwen
request through llama.cpp with LOCAL_ONLY routing and exact model authorization.
Compatible-endpoint failures/restarts are tested in a separate synthetic lab.
This supports evaluating a future local explanation transport, not a working POK
adapter. No POK code or workspace was changed. Moderation, trusted instruction
separation, cancellation, request provenance and POK's own consent/budget controls
remain required. Offline poker mathematics and gameplay remain independent of CAE.
See [M3 acceptance and limits](../validation/LOCAL-INFERENCE-M3-PACKAGED.md).
