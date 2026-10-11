# CAE Python client 0.4.0

Install this wheel and `codex-api-engine>=0.3.1,<1` on Windows/Python 3.14.
Set `CAE_CONNECTION_FILE` to the operator-provided connection descriptor, then:

```python
from cae_client import CAEClient
client = CAEClient()
print(client.connect())
print(client.health())
print(client.models())
```

The operator enrolls the executable; a Python interpreter enrollment applies to all
scripts using that interpreter. No provider key belongs in the application. Calls
open a fresh authenticated pipe; failed generation calls are never replayed.
