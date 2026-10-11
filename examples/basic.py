"""No credential values or environment variables needed in consuming applications."""

from cae import CAE

engine = CAE()
print(engine.configure())
print(engine.test_connection())
print(engine.list_models())
