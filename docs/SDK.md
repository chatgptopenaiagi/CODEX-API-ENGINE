# Public SDK v0.2

This page describes the retained v0.2 compatibility surface. For the current v0.3
capability SDK, see [Access Engine](ACCESS_ENGINE.md) and [migration](MIGRATION_0.3.md).

```python
from cae import CAE, CAEError

engine = CAE()
status = engine.configure()
report = engine.test_connection()
models = engine.list_models()
```

`configure()` inspects local state; it neither reads a source file nor provisions a
key. `get_status()` is offline. `test_connection()` returns a JSON-compatible report
instead of propagating expected operational failures. `list_models()` returns model
IDs and raises fixed-code `CAEError` subclasses for failures.

Applications never pass or receive API keys through `CAE`. Provision once using the
human console or `CredentialManager` administrator interface. A trusted host chooses
profiles and explicit grants:

```python
from cae import CAE
from cae.broker import Broker, Grant
from cae.credential import WindowsCredentialStore

broker = Broker(WindowsCredentialStore(), (
    Grant("report-app", "default", frozenset({"models", "responses"})),
))
engine = CAE(app="report-app", broker=broker)
# On a deliberate user action (may incur API charges):
# result = engine.create_response(model=chosen_model, input=user_text, max_output_tokens=256)
```

`create_response()` sends `store=False`, limits input size and output-token bounds,
does not enable tools, and does not automatically retry generation. Provider response
JSON (including usage when returned) is sanitized before it reaches the application.
This is request-level usage reporting, not an account billing/usage API.

The default console grant allows models only. A custom `app` without a matching host
grant is denied. Names select host policy; they are not remote authentication tokens.
Do not hand untrusted code the broker/store or execute it in the same process.

Methods are synchronous. Invoke them from a worker in UI/event-loop applications.
The host owns injected backends and policy. Errors expose fixed `.code`; `APIError`
also has sanitized `.kind` and optional HTTP `.status`. No provider error body is returned.
