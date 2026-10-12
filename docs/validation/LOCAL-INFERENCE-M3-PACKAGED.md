# M3 packaged inference and isolated recovery

Status: **LOCAL ACCEPTANCE PASS; remote final checkpoint pending** (2026-10-12).
M3 is scoped to packaged real inference plus disposable compatible-endpoint recovery.
**REAL_QWEN_RESTART_NOT_RUN**; no operator-managed server outage was injected.

## Revision and artifact identity

Started on `feat/security-registry` at `9b31d1460c64b255287e0a9cd7cdbf26b6e2bfee`,
version 0.5.0.dev4; remote was bf238e2773cc1ea39b0e684faa9ef8ab7b45b176.
Source/history scans passed; normal push and independent fresh GitHub recovery of
9b31d14 passed before any new implementation. Phase A CI passed: push 38205362464
and PR 38205364681. PR #2 remains open/draft; no main merge or release.

New development version: **0.5.0.dev5**. Runtime build source commit: `bf6107f52e73556176f0e92dd6fde81c5dabc8b2`; this follows dev5/client preparation `ea6add6`.
The following code changes are included: exact backslash model identifiers,
one-shot public-SDK console requests, and rejection of HTTP declared-length
truncation. No alternate broker, provider architecture or wire protocol was added.
The runtime-source check independently compares embedded Python code objects in
all four EXEs against source, and wheel/sdist module bytes against source.
Documentation-only package refresh does not change executable hashes.

Artifacts are under `dist/0.5.0.dev5/`; all development EXEs are unsigned.

| File | SHA-256 |
|---|---|
| `CAE-Broker.exe` | `16858ad20d53507b8b7b26aa8b50632ee0373c2f69d21c5a2fd00a6378698dc2` |
| `CAE-Console-Client.exe` | `588481bd742d89c2d72703ded8c442630e1ed6ed5d314063329acc6206778fd4` |
| `CAE-Control-Center.exe` | `8b79cc3fd836eebf166b74251bc3777cbcdf8de2899caf53be7f12dcecc3b52d` |
| `CAE-Desktop-Client.exe` | `dae6c69b4de0bb510488f234e99d9630d8d8ac32672eabe152b6a4a31022b0eb` |
| `codex_api_engine-0.5.0.dev5-py3-none-any.whl` | `86071af256cf7cd7d395e04cd4d20baaa8e1ea5dee65c4a5860068b58fbcd329` |
| `codex_api_engine-0.5.0.dev5.tar.gz` | `7b44f0187dfab313c4f31041d31fc2b5a95fd475bb9aa3777fd83dbd8befc0a8` |

`SHA256SUMS.json` contains these six digests. All four executable self-tests, archive
exclusion inspection, nonzero-file checks, package version and source-identity
verification passed. Older development artifacts were not overwritten. The initial
unvalidated dev5 candidate is retained under `.tmp/m3-dev5-before-framing-*`.
The sdist is an installable source package, not a complete Git checkout/test toolchain.

## Actual real-provider result — PASS

The operator-approved endpoint `http://127.0.0.1:8080` advertised exactly:
`I:\LocalAI\models\Qwen3-4B-Q4_K_M\Qwen3-4B-Q4_K_M.gguf`.
Only that endpoint was inspected; no port/LAN scan. The runtime is operator-managed
llama.cpp build 10665. No model hash was recomputed or model/configuration altered.

The **new packaged CAE-Console-Client.exe** called the **new packaged CAE-Broker.exe**
through Windows Named Pipes. Broker-reported version was 0.5.0.dev5, actual broker
PID 25256, authenticated consuming app `console` (the harness monitor is `lab`).
The server EXE path/hash was pinned, client image/hash enrolled, and both peers
verified through the existing Windows identity contract. The broker used the
existing `vllm` OpenAI-compatible wire adapter with provider ID `local`; this is
llama.cpp compatibility, not a claim that the server runs vLLM.

Synthetic input: “Reply with exactly: Local AI inference is operational.”
Final response: **Local AI inference is operational.**
Selected exact model matched the advertised/configured/requested/returned identity.
Mode: **LOCAL_ONLY**; fallback: **false**; dispatches: **1**; status: **COMPLETED**.
Provider-reported usage: **18 input / 81 output tokens**, CONFIRMED_USAGE. This is
not independently verified billing; output token counts may include reasoning.
Client process total time: **3622.08 ms**, including frozen-client startup/IPC.
Provider-only latency and broker-only overhead were not separately measured.
Request budget: 256 output tokens; client process deadline: 45 seconds; underlying
SDK deadline: 35 seconds. No sampling-setting change was made to the server.
Audit correlation ID: `4f0f99eefff14d23826561787cb23341`.

A second packaged-client request was denied by its daily quota. Audit inspection
confirmed exactly one real inference completion. Cloud-only was denied, with no
cloud providers configured and no cloud credentials accessed. No raw reasoning or
synthetic prompt/final content appeared in audit. The adapter selects only
`message.content`; reasoning_content is not exposed. No universal reasoning-hiding
guarantee for all future providers is implied. The normalized response does not
return server fingerprint or original finish reason (`UNKNOWN` remains honest).
The earlier 32-token/length diagnosis is retained in the source-level M3 report;
this mission did not repeat that probe.

## Isolated recovery — MOCK_ONLY / PASS

A separate Python HTTP server process binds literal loopback on an OS-assigned
port, never 8080. Only that child process tree is terminated. It implements the
compatible response shape but performs **no model inference**. The packaged broker
is genuine; provider results/faults are synthetic. Fresh requests recover after
the existing five-second advisory unhealthy-cache period, with no broker restart
unless the scenario explicitly tests an isolated broker restart.

Eighteen recorded scenario groups passed:

- Connection refusal before request, followed by endpoint startup.
- Endpoint process termination during an accepted request, then restart.
- Connection reset, malformed JSON, missing fields, wrong content type, wrong
  model, boolean token usage, oversized normalized output and oversized HTTP body.
- Temporary HTTP 503 and a truncated declared-length response.
- Provider header/read timeout: bounded failure after 15980.72 ms.
- Client timeout with a late response, concurrency denial while occupied, and
  subsequent release; the later request receives its own result, not DELAYED_FINAL.
- Three repeated unavailable/restarted endpoint cycles.
- Packaged-client unenrolled denial, enrollment, successful request, revocation,
  and persistent revocation after isolated broker restart.
- Daily quota persistence, counting a failed dispatch; UTC-minute quota persistence.

All dispatched fault cases returned fixed `request_outcome_unknown` without raw
exception/body/credential leakage or replay; selection-time denials remain distinct.
No outcome-unknown request is refunded automatically. Fresh requests after recovery
still use policy/quota/concurrency admission. A timed-out client is not evidence of
provider cancellation. Provider cancellation and isolated socket-write-stall injection
are NOT_RUN; no cancellation claim is made.

The malformed-response tests found a genuine defect: bounded `HTTPResponse.read(n)`
can return incomplete declared content without raising when bytes form valid JSON.
A new real-HTTP regression reproduced the false success, and the transport now rejects
remaining declared bytes. Unit and packaged tests pass after rebuilding. An earlier
harness assertion incorrectly required request IDs on non-request startup events;
it was corrected to verify the full authentication/policy/dispatch/completion chain.
The first regression run also found dev4-pinned version assertions; expectations now
match dev5. A new test's unclosed SQLite ledger warning was fixed with explicit cleanup.
No failed test was removed or coverage threshold reduced.

Managed audit storage rotated during the lab and recovered across broker restart:
32 archives, 125234 owned record bytes within the 262144 configured total limit,
272 retained events, zero rejected audit events. Real acceptance retained 12969 bytes
in three archives. Retention can remove older evidence according to the M1 contract;
checks require correlation for retained request events, not startup events.

Cold-to-post-cycle broker samples: handles 150→169, working set 30244864→32620544
bytes, private bytes 20320256→22241280. Restart sample: 156 handles. These short
measurements do not prove leak freedom or a long-running bound; follow-up resource
samples are recorded below. M6 soak/Windows 11 acceptance remains separate.

## Quality gates and compatibility

- **414 tests passed in 62.83s**, no skips or warnings reported in final run.
- **95.95%** statement coverage; all **18** critical module gates at least 95%.
- Ruff, strict engine/client mypy passed.
- Six actual Python/C#/C++/Node/PowerShell/Electron applications passed against the
  new packaged broker, using **mock** providers: broker PIDs 14688 then 21120,
  legacy requests, routed requests, client termination survival and restart recovery.
- **60 hostile-server cases passed**, five SDK languages.
- Installed-wheel and frozen legacy console/desktop acceptance passed: broker PID
  8720, desktop survives console termination, clean restart and crash recovery.
- Exact ID tests cover backslashes, drive-like prefixes, punctuation, 128 characters,
  exact match and explicit deny. Spaces, Unicode, controls, empty/oversized IDs,
  leading separators and query/fragment characters remain deliberately rejected.
  Repeated internal separators remain opaque strings, not file operations.
- Protocol v1, same-user process boundary and legacy clients remain unchanged.

## Reproduction

```powershell
./scripts/build.ps1 -Executable
./.venv/Scripts/python.exe scripts/checksums.py
./.venv/Scripts/python.exe scripts/check_release.py
./.venv/Scripts/python.exe scripts/check_artifacts.py --directory dist/0.5.0.dev5
./scripts/test.ps1
# Synthetic recovery only; CI uses this form:
./.venv/Scripts/python.exe scripts/validate_m3_packaged.py --broker-directory dist/0.5.0.dev5
# Only for the explicitly approved existing Qwen endpoint; makes ONE real call:
./.venv/Scripts/python.exe scripts/validate_m3_packaged.py --broker-directory dist/0.5.0.dev5 --real-qwen
./.venv/Scripts/python.exe scripts/validate_clients.py --broker-directory dist/0.5.0.dev5 --artifacts .tmp/m2-clients --results-directory .tmp/m3-native-final --managed-audit --routing --electron .tmp/electron-lab/node_modules/electron/dist/electron.exe
./.venv/Scripts/python.exe scripts/validate_client_security.py --integration-report .tmp/m3-native-final/CROSS-LANGUAGE-RESULTS.json
./scripts/test_broker_apps.ps1
```

Source/wheel/build dependencies follow the existing recovery instructions. On a
fresh clone build client packages first; `.tmp/m2-clients` is a preserved local lab
build, not a remote dependency. CI builds the same client source into its own output.
The standalone Qwen/recovery harness uses the public SDK for requests; only trusted
host-side enrollment/audit inspection imports broker configuration helpers.

Local evidence: `.tmp/m3-packaged-0cdea769156a47d68972313a95841068/RESULTS.json`,
`.tmp/m3-native-final/`, `.tmp/m3-packaged-preservation/tests-clean.log` and build logs.
Previous failed-run directories are preserved. Generated configs/logs are ignored
and not included in Git or distribution packages.

## Preservation, limitations and follow-up

41 historical artifact files retain their initial SHA-256 values; Git tag refs and
v0.2.0/v0.3.1 release/asset IDs, sizes and digests are unchanged. Protected input is
ignored and unchanged; the existing artifact checker compares it in memory only,
never emits it. Production vault/enrollment/audit state, broker and Qwen runtime
were not modified. No global PATH, CUDA/PyTorch, security policy, service or unrelated
repository was changed. Five unknown untracked user files remain uncommitted.

Actual host: Windows 10 build 19045, Python 3.14.7, PowerShell 7.6.6. Windows 11,
signing, same-user hostile-code isolation and long soak are not established.
No paid cloud inference, model download, real Qwen outage/restart, new release or
main merge. Loopback classification does not prove the local server cannot forward
network traffic. Six-language real Qwen execution is NOT_RUN; only the frozen Python
console performed real inference. No POK adapter exists; moderation, trusted roles,
cancellation, provenance and POK-owned consent/budgets remain integration gaps.

Final synchronization/recovery/CI evidence belongs in the continuity checkpoint.
After all in-scope M3 gates pass, M4 centralized administration is next; do not start
M4 as part of this acceptance mission.

## Additional bounded resource observations

A separate 40-request synthetic run sampled handles at requests 5/10/15/20/25/30/35/40:
164/170/170/170/170/170/170/170. Private bytes stayed 22269952 for samples 10 through
35 and ended at 22540288. The cold increase therefore is not evidence of a continually
growing handle leak; no zero-leak or soak guarantee is inferred. A separate three-cycle
cold run observed 156/160/164/168 handles, motivating worker warm-up before comparison.
The committed harness now warms the fixed worker set before its outage samples.
Reports: `.tmp/m3-resource-plateau-5712f219027b4631850fb95ad5053008/RESULTS.json`
and `.tmp/m3-resource-c311eb79b2ba4fe59aba483d1251ce9f/RESULTS.json`.

Final committed-harness mock rerun: PASS, all 18 groups; report
`.tmp/m3-packaged-9c1267d48bce4727967e03e3a70a3e6c/RESULTS.json`.
After 16 worker warm-up requests, handles were 171 before outage cycles and 169
after; private bytes 22646784 to 22585344, working bytes 32894976 to 32886784.
No post-warm-up growth observed in this bounded sample; not a soak guarantee.
Retained audit: 126076 bytes, 32 archives, zero rejected events. Endpoint calls 48
before separate daily/minute cases. No extra real Qwen call was made.

Final wheel installed with `pip --no-index --no-deps` into a fresh unique local
venv. `python -I` imported site-packages, verified dev5/exact model syntax and
synthetic content/usage normalization with reasoning exclusion: PASS, no credentials.
Publication audit: 180 Git-eligible files, zero Gitleaks findings. Only reviewed
mission files are staged; five existing untracked user files remain excluded.
