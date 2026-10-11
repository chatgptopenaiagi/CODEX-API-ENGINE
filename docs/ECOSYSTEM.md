# ARX, CGC and Codex integration contracts

CAE owns provider capability access, credentials, policy evaluation, connection
observations and metadata audit. ARX owns evidence/identity/trust reasoning. CGC owns
prompt, continuity, repository-memory and recovery state. Neither domain is implemented
inside CAE simply by naming it.

`cae.integrations` supplies typed `EvidenceRecord`, `EvidenceSink`, `ContinuitySink`
and an offline `snapshot(engine, system)` helper. Evidence records contain a random
record ID, observation time, system label, SDK version and broker/policy/provider
status. They contain no prompts, responses, API keys or credential history values.
Consumers may attach these references to their evidence registries or continuity
checkpoints. A health observation is not an identity claim or a trust decision.

Native integration entry points:

- ARX can implement `EvidenceSink.record` to register observations and audit event
  UUIDs, correlate its own authenticated identities and maintain credential-change
  evidence without storing credentials. CAE does not score trust.
- CGC can implement `ContinuitySink.checkpoint` to preserve access-state observations
  alongside its own prompts/work-state. CAE does not preserve or replay prompts.
- Codex can invoke `cae health`, `cae diagnostics`, `cae providers`, `cae policies`
  and `cae audit` for JSON metadata. Use explicit configuration/application labels;
  never copy keys into a repository or change Codex CLI login configuration.

No plugin modifies Codex internals, no external ARX/CGC repository is altered, and
no nonexistent integrations are advertised as deployed products. These are typed,
tested host interfaces that future projects can implement.
