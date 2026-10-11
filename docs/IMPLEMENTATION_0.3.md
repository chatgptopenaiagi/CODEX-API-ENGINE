# v0.3.0 implementation record and plan

Completed foundation:

1. Preserve v0.2.0 release and protected credentials; develop on `feat/codex-access-engine`.
2. Introduce typed provider adapters, capability sessions and a trusted composition root.
3. Add strict TOML policy, deny precedence, model scopes and atomic durable daily quotas.
4. Add metadata-only durable audit, normalized health/latency and observed usage.
5. Extend Windows credential namespaces without migrating the existing OpenAI target.
6. Expose the new SDK/CLI and a separate human Control Center.
7. Add ARX/CGC metadata contracts and Codex diagnostic usage.
8. Run compatibility, provider-contract, negative policy, concurrency, persistence,
   redaction, packaging and UI smoke checks; create separate v0.3.0 artifacts.

Future security milestones: separate-identity Windows service, authenticated named-pipe
IPC, durable administrator policy enforcement across hostile processes, signed builds,
log integrity/retention controls, async/streaming cancellation, live provider certification
and consumer-owned ARX/CGC implementations. These are not silently approximated by
in-process Python permissions.
