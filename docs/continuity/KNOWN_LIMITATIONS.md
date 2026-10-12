## Experimental preservation checkpoint (2026-10-12)

The explicit preservation-only mission supersedes the earlier M4 completion-dependent
publication hold. No runtime source or existing binary was changed or rebuilt.
Published experimental prerelease (30 assets; all download hashes PASS): `v0.5.0.dev6-preservation`, source `2a300a0d96a0e8f2ad102940e4a9775d5d256608`;
binary build `5a0020ca674d157c1213572ac7f7910157805ed5`. See
[the preservation evidence](../validation/PRESERVATION-0.5.0.dev6.md) for actual
publication/download status and [artifact inventory](../validation/DEV6_ARTIFACT_INVENTORY.json).
M0-M3 remain complete within recorded scope; M4/M6 PARTIAL, M5/M7 PLANNED.
The first future development task remains confirmed authorization/routing/quota GUI
forms, then safe first-run provisioning. Do not develop during preservation.
Installer, signing, Windows 11 and POK integration remain incomplete/unverified.
Earlier RELEASE_NOT_PUBLISHED/BLOCKED statements below describe historical M4
candidate gates, not a prohibition on this authorized experimental preservation.

# Known limitations

## M4 current checkpoint

M4 dev6 is not a complete beginner installation. An operator-provided configuration and pre-enrolled administrator image are required. Remembered descriptor is same-account private state, not an OS isolation boundary. No automatic broker start, enrollment or cloud request. Graphical authorization/routing/quota/provider edits and broker audit display remain unfinished. Prerelease withheld: bundled-DLL notices incomplete. No installer, Windows 11 acceptance or GitHub-download evidence.


## M3 current limits

Packaged real Qwen inference and isolated compatible-endpoint recovery passed.
Real Qwen restart/outage, cancellation, network-level offline isolation, Windows 11
and long soak remain NOT_RUN. Dev5 packages contain the exact-model and truncated-
HTTP fixes; dev4 is preserved. Only the packaged Python console used real Qwen;
six-language acceptance used mocks. Normalized results do not expose provider
fingerprint/finish reason. [Evidence](../validation/LOCAL-INFERENCE-M3-PACKAGED.md).

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
  Real dev5 Qwen chat passed; recovery injection uses a mock HTTP provider.
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
application provenance remain unsupported. No POK adapter; real Qwen chat does not validate all providers.
See [M2 limits and evidence](../validation/ROUTING-M2.md).
