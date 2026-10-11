# Independent Windows broker protocol — v1

CAE v0.3.1 implements a real user-launched Windows process, not a Windows SCM service.
Start `CAE-Broker.exe --config <absolute broker.json>` directly, or use the lifecycle
CLI documented in README. No auto-start registration or Windows component is changed.
`CAE()` remains the compatibility SDK for trusted in-process hosting. External clients
use `BrokerClient`, which never loads a credential or accepts an application identity.

## Enrollment and connection

Run `python scripts/enroll_broker.py --artifacts dist/0.3.1 --directory .cae/broker`
from the repository. It refuses to overwrite an existing enrollment. It creates:

- `broker.json`: schema version 1, local pipe name, absolute runtime TOML path,
  server image/hash, and client image/hash/application/admin enrollments.
- `runtime.toml`: existing provider and policy schema, with read-only OpenAI grants
  for the two examples and operator. The existing default credential is reused.
- `client.json`: pipe name, server image path and SHA-256; no provider credential.

The helper grants admin to the actual Python process image executing it. On Windows
a virtual-environment launcher may execute the base Python image. All programs using
that image share this enrollment. Use frozen, separately enrolled executables for
distinct application policies; interpreter enrollment is a trusted operator choice.
Protect enrollment, runtime TOML, state, and executable files from untrusted writes.
Remove a client enrollment and restart to revoke its future IPC access. Changes are
not hot-reloaded. Rebuilds require new hashes and explicit reviewed enrollment.

The pipe name is `\\.\pipe\cae-<validated suffix>`; UNC hosts and arbitrary paths are
rejected. PIPE_REJECT_REMOTE_CLIENTS is enabled. A protected DACL grants access only
to the current user SID and SYSTEM. The first server instance uses
FILE_FLAG_FIRST_PIPE_INSTANCE. Eight fixed workers retain their pipe instances.
SYSTEM is permitted by the DACL but client authentication still requires the broker's
user SID. Client connection handles request identification-level security only.

For every connection, the server queries GetNamedPipeClientProcessId, opens that
process, reads its token user SID and image path, and compares path and SHA-256 against
the enrollment. The client independently uses GetNamedPipeServerProcessId and checks
the server SID, image path and hash. These are OS-authenticated connections; no shared
API key, bearer-session token, client-supplied app name or plaintext credential is used.

## Framing and schema

Byte-mode duplex pipe. Each message is a four-byte unsigned little-endian length,
followed by 1–65,536 bytes of UTF-8 JSON. Reject duplicate JSON keys, non-finite numbers,
unknown request fields and malformed types. Each connection serves exactly one request
and one response. The client then sends the framed two-byte payload `OK`, allowing the
server to disconnect without unbounded FlushFileBuffers. This acknowledgment does not
authorize another action. EOF, incomplete frames and missing acknowledgments time out.

Request:

```json
{"v":1,"id":"0123456789abcdef0123456789abcdef","op":"diagnostics","args":{"provider":"openai","profile":"default"}}
```

Response includes exactly `v`, matching `id`, boolean `ok`, object `result`, fixed
`error` code or null, and OS broker PID. Malformed requests that lack a valid ID receive
32 zeros. Provider exception text, prompts, keys, headers and arbitrary stack traces
are never error fields. Oversized responses produce `invalid_protocol`, not truncation.

Operations:

| Operation | Authorization / behavior |
|---|---|
| status | Enrolled client; PID, mode, version, authenticated app, bounded counters |
| diagnostics | Existing diagnostics capability; offline provider/credential metadata |
| health | Offline by default; `probe: true` requires health capability and makes models GET |
| models | Existing models capability and quota; normalized provider response |
| chat, embeddings | Existing operation, provider/profile and model policy; quota |
| usage | Existing usage capability; runtime observations |
| providers, policies, audit | Enrolled client's own visible metadata; audit last 50 events |
| stop | Explicit administrator enrollment only; drain and close |

Arguments are limited to provider/profile, health's boolean probe, and chat/embedding
model/text/max_tokens. No endpoint, application identity, credential, policy-mutation
or export argument exists. Unknown operations are denied. Policy denial precedes vault
access. UTC-day quotas and metadata audit persist beside the configured runtime TOML.
SDK clients do not call the vault. Existing human credential administration remains
separate from this protocol; production credential targets are unchanged.

## Installed SDK

```python
import json
from pathlib import Path
from cae import BrokerClient

client = BrokerClient(**json.loads(Path("client.json").read_text()))
print(client.get_status())
print(client.diagnostics())        # Offline
# Explicit minimal authenticated request, when desired:
# print(client.health(probe=True))
# print(client.list_models())
# Requires a separately granted model/operation:
# print(client.chat("approved-model", "hello", max_tokens=64))
```

Install the wheel first. Client source examples import only `BrokerClient` and
`CAEError` from the public `cae` package. Frozen clients need no Python installation.
The example console/Desktop clients poll status/diagnostics. The test-only
`--verify-denial` flag additionally attempts administrative shutdown and requires it
to be denied; use that flag only with non-admin client enrollments. Close the console with Ctrl+C and the desktop
with its window close button. Automation options write only fixed metadata reports.

## Timeouts, shutdown and crashes

Connect attempts default to three seconds. Server request receive and acknowledgment
deadlines are two seconds each; send deadline is three seconds. Maximum eight active
connections; additional clients wait briefly or fail with broker_unavailable. Each
call opens a fresh connection. No request is automatically replayed after failure.
Provider socket operations have a 15-second timeout and a separate 20-second
post-connect timer interrupts slow header/body transfers. OS DNS resolution is not a
hard real-time guarantee. A disconnected client cannot cancel an already accepted
provider action; its quota remains charged. Do not retry generation blindly.

Stop signals all listeners, waits for active workers and closes the quota ledger.
The supervisor reports failure if shutdown exceeds its wait; it never force-kills
arbitrary processes. Start pins the configured CAE-Broker.exe and returns authenticated
status. Restart performs stop then start. Crashes release native pipe handles;
explicit start recovers without trusting stale PID files. No watchdog is installed.

## Security limits and references

This is not strong OS isolation between programs running as the same user. Such code
may access the same credential vault, change configuration or executable files, inject
into processes, or exhaust resources. Executable file hashes do not attest loaded code,
interpreted scripts, plugins or process integrity. There is no cross-user delegation,
separate service account, Authenticode validation, or per-logon-session restriction.
Use a dedicated service identity and protected deployment before treating hostile
same-account applications as isolated tenants.

Win32 design references: [named-pipe security](https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights),
[kernel client PID](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getnamedpipeclientprocessid),
and [client impersonation controls](https://learn.microsoft.com/en-us/windows/win32/ipc/impersonating-a-named-pipe-client).
