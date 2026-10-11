# Diagnostics and health monitoring

`CAE.get_status()` returns schema version 1 with:

| Field | Meaning |
|---|---|
| `sdk_version` / `schema_version` | Installed SDK and report format |
| `engine` / `configured` | Whether the permitted profile is stored |
| `credential` | `stored`, `missing`, or `unavailable` |
| `broker` / `broker_mode` | Local permission/backend readiness; `in_process` |
| `authentication` | `unknown`, `valid`, `invalid`, `permission_denied` |
| `api` | `unknown`, `available`, `reachable`, `unavailable` |
| `checked_at` | UTC ISO timestamp of last explicit probe, otherwise null |
| `error` | Fixed safe classification, otherwise null |

A 401 means the credential was rejected; 403 means insufficient permission. A 429
or server error proves the endpoint responded but does not prove credential validity.
Network/TLS failures report unavailable and unknown authentication. A successful model
list proves that operation only, not access to every model, quota or billing capability.

Snapshots do not trigger network traffic. They retain last-probe health with a timestamp;
consumers must choose their own freshness threshold. If another process replaces a key,
the previous authentication result remains historical until a new probe.

```python
from cae import CAE
from cae.monitor import HealthMonitor

monitor = HealthMonitor(CAE(), interval=300)
report = monitor.poll()  # One explicit request
# Optional background polling; keep the context open for the desired lifetime:
# with monitor:
#     run_application()
```

Monitoring is opt-in, uses one model-list request per poll, and has a minimum 30-second
interval. `stop()` signals shutdown and waits up to its timeout for an in-flight call.
Do not log requests, keys, tracebacks with locals or full transport exception objects.
