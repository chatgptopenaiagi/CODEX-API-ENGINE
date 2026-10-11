# Six unfinished milestones toward v1.0

Next milestone: audit logging improvements.

## 1. Audit correlation and bounded retention

Current: `src/cae/audit.py` provides allowlisted metadata events and bounded memory;
the optional JSONL file is unbounded. Missing: shared request correlation, decision,
status, latency, error metadata and safe disk rotation. Dependencies: broker request
lifecycle (`broker_service.py`, `access.py`) and backward-compatible event schema.
Implement metadata-only enrichment and explicit retention configuration. Acceptance:
one request trace spans authorization/result; no prompts, results or secrets logged;
concurrent writes, restart, full disk and rotation failure preserve fail-closed
behavior and bounded storage. Extend audit/security and real-process tests.

## 2. Capability-based provider routing

Current: `providers.py`, `access.py`, `policy.py` support explicit provider selection
and restrictions. Missing: capability selection, preferences, local-first/offline-only
rules and controlled fallback. Depends on truthful provider capability descriptors
and policy checks before vault/provider access. Acceptance: routing only selects
authorized providers/models, offline/confidential requests never reach cloud, and
ambiguous billable failures are never automatically replayed. Test with multiple
mock endpoints, denied routes, outages and accounting; then live authorized checks.

## 3. Real local-model validation

Current: Ollama/vLLM/LM Studio adapters are mock-tested, no real inference evidenced.
Default local ports did not respond in the previous development session; this is
not a full machine inventory. Depends on an available user-approved local runtime
and model. Use `providers.py` and existing SDK/lab interfaces. Acceptance: actual
model discovery, health and inference through broker with recorded runtime/model,
offline verification and permission denial. Clearly distinguish mock from live
results; do not install large runtimes or redirect workloads silently.

## 4. Centralized administration

Current: `registry.py`/`cli.py` provide operator commands; `control_center.py` remains
the existing trusted GUI. Missing: registry/authorization/revocation GUI, provider
policy management and broker-centered human diagnostics. Depends on a defined
authenticated administrative boundary; ordinary applications cannot grant rights.
Acceptance: explicit human changes, read-only mode, validated edits, GUI closure
leaves broker alive, revoked clients denied, no keys in IPC. Test UI operations,
policy failures and independent process behavior without production configuration.

## 5. Windows installation infrastructure

Current: build scripts produce standalone EXEs and packages, no installer/uninstaller.
Missing: user-scoped installation, enrollment, broker discovery, first-run flow,
double-click startup, optional startup and upgrades. Depends on validated identity,
ACL and configuration-location rules (`broker_control.py`, `ipc_protocol.py`).
Acceptance: clean install/upgrade/uninstall on disposable Windows host; preserve
credentials and user policy/enrollment data, opt-in removal only, no unnecessary
elevation or permanent PATH changes. Test rollback, locked files and reinstall.

## 6. Long-running reliability and stable acceptance

Current: real short lifecycle/crash/restart/concurrent-client tests pass. Missing:
soak, sustained resource monitoring, upgrade recovery, cancellation, Windows 11
acceptance, signing and independent security review. Depends on the previous
milestones and versioned protocol/config migration rules. Relevant modules:
`broker_service.py`, `broker_control.py`, `pipe_transport.py`, policy/audit persistence.
Acceptance: bounded resources under long load, controlled outage/recovery, no
unauthorized provider calls, explicit compatibility results, reproducible artifacts
and no critical unresolved findings. Publish stable v1.0 only after evidence and
separate human release authorization. No completion dates are assumed.

