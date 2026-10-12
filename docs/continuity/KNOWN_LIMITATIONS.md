# Known limitations

## M3 local checkpoint

M3 update: real Qwen chat inference is now validated through an isolated source broker. Provider restart, cancellation, network-level offline isolation and updated executable acceptance remain NOT_RUN. Existing dev4 binaries lack the Windows model-ID fix. Historical mock-only statements below describe the preceding M2 evidence. [Current report](../validation/LOCAL-INFERENCE-M3.md).


- Same Windows account can access its vault and writable configuration. SID and
  executable hashes do not attest loaded code or isolate hostile same-user programs.
- Interpreter enrollment covers the interpreter image, not every script/module.
- Policy edits require restart. New broker enrollment revocation applies on the
  next connection; in-flight accepted work may finish. v0.3.1 needs restart.
- Fixed UTC-minute limits trust the system clock; concurrency limits are per runtime.
- Old native 0.4 clients may report new rate/concurrency errors as generic broker
  request failure. There is no generation replay on transport errors.
- Installer, central registry GUI, cancellation, soak/upgrade
  recovery and separate service identity are unfinished. Managed audit retention is
  opt-in; legacy stores remain unbounded. Age pruning is event-driven, not a timer.
  Complete corruption fails closed; process-crash recovery is not power-loss proof.
  Filesystem I/O itself has no hard deadline; lock waits are bounded.
- Seven adapters are implemented, but all-provider live validation is not claimed.
  Local inference has not been validated. Current acceptance uses a mock HTTP provider.
- Actual host is Windows 10 build 19045; Windows 11 acceptance remains unverified.
  Current executables are unsigned. Python coverage is not native SDK coverage or
  an independent security assessment.
- Development artifacts/caches are not stored in Git. Fresh recovery needs installed
  toolchains and dependency downloads. Builds are not proven bit-for-bit reproducible.
- The operator explicitly deferred the five-repository requirement. Only CAE may be changed;
  ARX/CGC references describe optional contracts, not implemented external integrations.

See [remaining acceptance criteria](UNFINISHED_MILESTONES.md) and
[remote status](GITHUB_STATE.md). Historical validation is retained as dated evidence.

M1 correlation is broker-local, not an end-to-end caller provenance token. ipc_result
records response preparation, not delivery acknowledgement. See [M1 evidence](../validation/AUDIT-M1.md).


M2 routing is opt-in, using exact configured models and per-provider rule budgets.
It does not create an application-wide monetary budget. Legacy explicit-provider
permissions remain; new routing restrictions do not revoke them. Local-first cloud
fallback is pre-dispatch only, with dual permission; no failed dispatch is replayed.
Locality constrains CAE's endpoint, not forwarding by a local server. Availability
is a five-second observation, not guaranteed reachability. Provider aliases may be
rejected by exact returned-model validation. Unknown token usage is not zero.
Moderation, privileged instructions, streaming, provider cancellation and end-to-end
application provenance remain unsupported. No POK adapter or live-model acceptance.
See [M2 limits and evidence](../validation/ROUTING-M2.md).
