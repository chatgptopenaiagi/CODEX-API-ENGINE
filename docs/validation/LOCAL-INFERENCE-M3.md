# M3 real local inference — 2026-10-12

**CAE-routed inference PASS; M3 broader acceptance PARTIAL.** This is real model
execution, not a mock. Starting commit: `bf238e2773cc1ea39b0e684faa9ef8ab7b45b176`,
branch `feat/security-registry`, source version `0.5.0.dev4`. Resolve the resulting
local checkpoint with `git log -1 --format=%H -- docs/validation/LOCAL-INFERENCE-M3.md`.
No public synchronization or release is part of this local checkpoint.

## Implementation and boundary

One narrow source change permits backslashes in bounded model identifiers. They
remain opaque, case-sensitive exact allowlist entries, never filesystem operands.
No path normalization, file reading, model alias or authorization expansion occurs.
The existing `vllm` adapter's OpenAI-compatible wire implementation is reused for
llama.cpp; the provider ID is `llamacpp`. This does not identify the runtime as vLLM
or establish embedding support. Protocol v1 and existing M1/M2 decisions remain.

The endpoint is the explicitly approved `http://127.0.0.1:8080`. GET `/v1/models`
confirmed exactly `I:\LocalAI\models\Qwen3-4B-Q4_K_M\Qwen3-4B-Q4_K_M.gguf`.
Read-only process inspection found `I:\LocalAI\runtime\llama-b10665\llama-server.exe`
PID 25680, listening on 127.0.0.1:8080. The response fingerprint was
`b10665-ca3d5a3e1`. Operator-supplied model SHA-256:
`7485FE6F11AF29433BC51CAB58009521F205840F5B4AE3A32FA7F92E8534FDF5`.
The model file hash was not independently recomputed; CAE neither loaded nor changed it.

## Executed acceptance

Final isolated source broker PID **10016**, Python launcher PID **30384**.
The client uses public `BrokerClient`, whose named-pipe verification checks the
server's OS identity; the broker authenticates the enrolled interpreter image.
All configuration, quota and audit files are in a unique repository-local `.tmp`
directory. No production configuration, vault entry or broker was used.

| Check | Result |
|---|---|
| Real model discovery | PASS |
| OS-authenticated independent broker/client | PASS |
| LOCAL_ONLY real generation | PASS |
| Cloud mode, unknown model, client administrative shutdown denial | PASS |
| Concurrent real request denied at limit 1 | PASS |
| Daily limit 5; subsequent request denied | PASS |
| Enrollment revocation on next connection | PASS |
| Client timeout; accepted inference completes without replay | PASS |
| Exactly five completed dispatches including timed-out call | PASS |
| Clean isolated broker exit | PASS, exit 0 |
| Managed audit excludes synthetic prompt, final content and reasoning field | PASS |

Synthetic final response: **Local AI inference is operational.**
First routed response latency: **2657.27 ms**. Exact model ID and provider ID were
returned; provider-reported usage was **18 input / 96 output tokens**. These are
reported tokens, not billing data; output tokens can include reasoning generation.
The existing normalized contract does not return the server fingerprint or original
finish reason; routing metadata honestly retains `provider_finish_reason: UNKNOWN`.
The report associates the observed fingerprint with the approved endpoint separately.
No temperature override was added to CAE; the direct diagnostic used temperature 0,
while routed calls used the existing adapter's server-default temperature.

The direct 32-token diagnostic returned `finish_reason: length`, zero final-content
characters, 133 reasoning characters, and 32 completion tokens. This supports token
exhaustion during reasoning as the explanation for empty final text. Reasoning was
counted in memory only, never persisted or printed. Normalization takes only
`message.content`; six new tests prove exact model matching, reasoning exclusion,
empty-content rejection despite nonzero usage, and bounded invalid-ID rejection.

Real cloud denial used a configuration containing only the authorized local provider,
with cloud/fallback permission false. No cloud credential or request was involved.
M2's mock tests cover mixed local/cloud candidate sets; this test does not claim
packet-level isolation or protection against a local server forwarding externally.

## Reproduction and regression

```powershell
# Only while this exact operator-approved endpoint/model remains available:
./.venv/Scripts/python.exe scripts/validate_local_inference.py --run-approved-local
./scripts/test.ps1
./.venv/Scripts/python.exe -m ruff check scripts/validate_local_inference.py tests/test_llamacpp_compatibility.py
```

All commands exited 0 for the final runs. Full gates: **399 passed in 60.17s**, no
skips reported, **95.92%** statement coverage, all **18** critical-module gates at
least 95%, Ruff and strict mypy passed. Existing M1 storage/correlation, M2 routing,
revocation, quota, lifecycle, native failure and supervisor tests ran in this suite.
Real client timeout is not provider cancellation. Provider timeout/failure behavior
is covered by regression injection, not by disrupting the operator's real server.

Final local raw report (synthetic final content, no reasoning):
`.tmp/m3-local-6eeaaf7e0a114d1f93ae3b891f47a15f/RESULTS.json`.
Managed audit concatenation SHA-256:
`5d29e59aba5e2a49eff43934b9362ab7ecbcfb86b332b520297ad8445d850add`.
Earlier runs are preserved. The first harness attempt failed an incorrect launcher
PID equality assertion; the verified peer PID is used now. Another successful run
used smaller retention limits; the final run retains all five completion records.

## Preservation and remaining acceptance

Production v0.3.1 broker PIDs 24596/10268 retain their 2026-10-11 creation times.
No production credential/file/log, server setting, global PATH, model installation,
Windows security setting, POK repository, historical tag or artifact was changed.
`apy_key.txt` remains ignored and was not read. Unknown untracked files remain.
Host: Windows 10 build 19045, Python 3.14.7; Windows 11 remains NOT_RUN.

NOT_RUN: real provider restart/outage recovery, provider-side cancellation,
packet-level offline proof, new frozen executable/package acceptance, six-language
real-model acceptance, and model-file hash recomputation. Existing dev4 artifacts
are unchanged and **do not contain the backslash compatibility change**. Do not
overwrite them; a future build needs a new development version/output directory.
No claim of complete M3 or production readiness. Next: validate remaining M3
recovery scenarios without interrupting this operator-managed inference server,
then build distinct artifacts and test their exact-model path.

Publication-safety scan: `scripts/audit_publication.py --gitleaks .tmp/gitleaks/gitleaks.exe` exited 0; 177 Git-eligible files scanned, zero findings (redacted scanner output). Only reviewed mission files are staged; five existing untracked user files remain outside the commit.

## Subsequent packaged acceptance

The source-only results above are historical. Follow-up dev5 packaged real inference
and isolated outage/recovery evidence is in [LOCAL-INFERENCE-M3-PACKAGED](LOCAL-INFERENCE-M3-PACKAGED.md).
The operator-managed real Qwen server was not restarted or reconfigured.
