"""Explicit policy composition by a trusted application host. Generation may incur cost."""

from cae import CAE
from cae.broker import Broker, Grant
from cae.credential import WindowsCredentialStore

broker = Broker(
    WindowsCredentialStore(), (Grant("my-app", "default", frozenset({"models", "responses"})),)
)
engine = CAE(app="my-app", broker=broker)
print(engine.get_status())
# Only on an explicit user action:
# response = engine.create_response(model="<model available to your project>", input="Hello")
