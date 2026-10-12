# Milestone status toward v1.0

## M3 local checkpoint

M3 current state: real routed llama.cpp/Qwen inference and authorization/resource denials PASS. Still PARTIAL: remaining real recovery/packaging acceptance is documented in [LOCAL-INFERENCE-M3](../validation/LOCAL-INFERENCE-M3.md). Do not repeat endpoint discovery or claim that no local inference has occurred.


M1 and M2 are COMPLETE within their documented contracts. Next: M3 real
local-model validation. No live inference is implied by the mock-tested milestones.

## 1. Audit correlation and bounded retention — COMPLETE

Correlation, explicit managed byte/count/age limits, Windows writer locks,
recoverable rotation/deletion intents and partial-tail recovery are implemented.
See [the current report](../validation/AUDIT-M1-RETENTION-ROTATION.md) for PASS/NOT_RUN
boundaries. Legacy opt-out stores remain unchanged and unbounded. Power-loss,
hostile same-user isolation and long-soak/Windows 11 validation are not claimed.
Do not reimplement M1. Windows 11 and long-running acceptance remain part of M6.

## 2. Capability-based provider routing — COMPLETE

Implemented: versioned chat/embedding contracts, opt-in routing policies, deterministic
provider/model selection, local-only/local-first/cloud-only/explicit selection,
controlled pre-dispatch fallback, unknown-outcome handling, existing quota/concurrency
and audit integration. Six real applications and mock providers exercise the new
protocol operations. See [M2 acceptance](../validation/ROUTING-M2.md) for final gates
and publication/recovery status. No real inference or POK integration is implied.

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
