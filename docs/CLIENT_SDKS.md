# Universal client SDKs — 0.4.0 development

These clients use the **existing broker protocol v1**. The engine and preserved
broker binary remain 0.3.1; client distributions have their own version 0.4.0.
No new public release or package-registry publication is implied.

## Discover, enroll, connect

1. Install the appropriate client package below.
2. An operator enrolls the executable's absolute image path and SHA-256 in
   `broker.json`, assigns its application label rules in `runtime.toml`, and
   restarts the broker. See [enrollment](BROKER_PROTOCOL.md).
3. Set `CAE_CONNECTION_FILE` to the absolute path of the operator-provided
   `client.json`, or pass its path to the SDK constructor.
4. Call `connect`/`ConnectAsync` and then the authorized operation.

The descriptor has exactly `pipe`, `server_image`, `server_sha256`. It contains no
provider credential. There is no implicit discovery from arbitrary working
directories, network discovery, auto-enrollment or permission self-grant.
Protect the descriptor, enrollment, policy and executable files against modification.

Every connection independently verifies the kernel server PID, Windows user SID,
image path and SHA-256 **before sending the request**. The broker independently
authenticates the actual client process. A request/response negotiates protocol v1
through its version field; unsupported versions fail. `connect` returns the engine
version, broker PID and authenticated app. `capabilities` returns only the provider
capabilities visible to that app, not unsupported future AI features.

## Packages and examples

Run `scripts/build_clients.ps1` from the repository. It requires Python 3.14,
.NET SDK 10.0.401, LLVM/clang++, MSVC x64 tools and a Windows SDK. Dependencies are
downloaded from official Node/nlohmann sources and SHA-256 pinned. Output is
`dist/0.4.0-clients/`; it does not rebuild or overwrite the broker or old releases.
The new C++ and .NET example executables are unsigned; .NET requires its runtime.

| Language | Package/source | Runtime |
|---|---|---|
| Python | `python/cae_client-0.4.0-py3-none-any.whl` | Python 3.14 and `codex-api-engine>=0.3.1,<1` |
| C# | `dotnet/Cae.Client.0.4.0.nupkg` | .NET 8+ on Windows |
| C++ | `cpp/include/cae_client.hpp` and bundled nlohmann header | C++20, Win32, bcrypt, advapi32 |
| Node.js | `nodejs/cae-client-0.4.0.tgz` | Windows x64, Node 22+; tested Node 26.8.1 |
| PowerShell | `powershell/CAE/` module and bundled .NET DLL | PowerShell 7.4+ |
| Electron | Same Node SDK in trusted main process | Electron main process; renderer has no Node access |

```powershell
python -m pip install .\dist\0.3.1\codex_api_engine-0.3.1-py3-none-any.whl .\dist\0.4.0-clients\python\cae_client-0.4.0-py3-none-any.whl
$env:CAE_CONNECTION_FILE = 'I:\CODEX-API-ENGINE\.cae\broker\client.json'
```

```python
from cae_client import CAEClient
client = CAEClient()
print(client.connect())
print(client.health())
print(client.models())
print(client.capabilities())
```

```csharp
using Cae;
var client = new CaeClient();
var status = await client.ConnectAsync();
var health = await client.HealthAsync();
var models = await client.ModelsAsync();
```

Add the repository-local NuGet directory as a source when installing `Cae.Client`
0.4.0 in a consuming project. The SDK depends only on the .NET framework.

```cpp
#include "cae_client.hpp"
cae::CAEClient client;
auto status = client.connect();
auto models = client.models();
```

Compile with the packaged include directory, C++20 and `advapi32.lib bcrypt.lib`.
The SDK returns nlohmann JSON objects and throws `cae::Error` with fixed codes.

```javascript
const { CAEClient } = require('@cae/client');
const client = new CAEClient();
const status = await client.connect();
const models = await client.models();
```

Install the local tarball using `npm install <path>/cae-client-0.4.0.tgz`.
The native Node-API module runs in worker threads in the calling process, not a
helper process. Up to eight concurrent calls per client instance are allowed.
The Windows delay-load hook resolves Node-API from the actual Node/Electron host.

```powershell
Import-Module .\dist\0.4.0-clients\powershell\CAE\CAE.psd1
Connect-CAE
Get-CAEHealth
Get-CAEModels
Get-CAECapabilities
```

All clients also expose generic `request`/`RequestAsync`/`Invoke-CAERequest` for the
documented operations, including authorized chat and embeddings. Applications
cannot add capabilities by calling that method. Provider/profile defaults are
OpenAI/default; select an explicitly configured local provider when desired.

## Failures and recovery

Requests have bounded frames (64 KiB), strict response correlation and fixed error
codes. C++/.NET/Node default to a 35-second request I/O deadline, at most three
seconds for connecting. Python retains the public v0.3.1 SDK's separate connect,
send and receive deadlines. Local synchronous executable hashing/file access is
not a hard real-time guarantee. Cancellation of .NET RequestAsync closes its
connection; it cannot cancel a provider action already accepted by the broker.

There is **no automatic replay**, especially for potentially billable operations.
After failure, a subsequent caller-initiated request opens a fresh connection and
revalidates the server. A rebuilt broker needs an operator-approved new pin.
The integration lab polls fresh read-only requests to demonstrate restart recovery.

Windows SID/image enrollment does not isolate scripts, plugins or hostile programs
running under the same user. Enrolling Python, Node, PowerShell or Electron grants
the same identity to all code using that executable. Use separately packaged images
for independently managed applications. On-disk hashes do not attest loaded code.

## Executed acceptance

`scripts/validate_clients.py` installs the Python wheel in a fresh environment and
the Node tarball without package install scripts. It runs five independent processes
against one unchanged `dist/0.3.1/CAE-Broker.exe`, with a loopback **mock** provider.
It verifies shared PID, models/health/capabilities, denied administration and spoofing,
denied generation before any provider POST, redaction, client termination resilience,
restart recovery and graceful shutdown. The operator's broker is not stopped.

`scripts/validate_client_security.py` uses a hostile test pipe server for 60 cases
across five languages: wrong pins/images, correlation/PID/version, duplicate keys,
invalid result, oversized/truncated frames, timeouts and error redaction. Wrong-pin
tests assert that the test server receives **no request bytes**.

Optional Electron acceptance:

```powershell
./scripts/setup_electron_lab.ps1
./.venv/Scripts/python.exe scripts/validate_clients.py --electron .tmp/electron-lab/node_modules/electron/dist/electron.exe
```

See [validation evidence](validation/CLIENTS-0.4.0.md) for measured results and
remaining limits. CI definitions exercise the five mandatory languages without
production credentials. Remote CI execution requires a later authorized push.
