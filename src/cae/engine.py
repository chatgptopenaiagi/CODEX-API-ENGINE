"""Versioned, secret-free application SDK."""

from datetime import UTC, datetime
from threading import RLock
from typing import Any

from .broker import Broker, Grant
from .credential import WindowsCredentialStore
from .errors import APIError, CAEError, ConfigurationError
from .security import identifier
from .version import __version__


class CAE:
    def __init__(
        self, profile: str = "default", *, app: str = "cae-console", broker: Broker | None = None
    ) -> None:
        self._profile = identifier(profile)
        self._app = identifier(app)
        # The built-in console is read-only. Generation requires an explicit host grant.
        self._broker = (
            broker
            if broker is not None
            else Broker(
                WindowsCredentialStore(),
                (Grant("cae-console", self._profile, frozenset({"models"})),),
            )
        )
        self._lock = RLock()
        self._health: dict[str, Any] = {
            "authentication": "unknown",
            "api": "unknown",
            "checked_at": None,
            "error": None,
        }

    def configure(self) -> dict[str, Any]:
        return self.get_status()

    def get_status(self) -> dict[str, Any]:
        credential = "missing"
        broker_status = "ready"
        try:
            credential = (
                "stored" if self._broker.configured(self._app, self._profile) else "missing"
            )
        except CAEError:
            credential, broker_status = "unavailable", "denied_or_unavailable"
        with self._lock:
            snapshot = dict(self._health)
        return {
            "sdk_version": __version__,
            "schema_version": 1,
            "engine": "ready" if credential == "stored" else "not_configured",
            "configured": credential == "stored",
            "credential": credential,
            "broker": broker_status,
            "broker_mode": "in_process",
            **snapshot,
        }

    def test_connection(self) -> dict[str, Any]:
        state: dict[str, Any] = {"authentication": "unknown", "api": "unknown", "error": None}
        try:
            result = self._broker.execute(self._app, self._profile, "models", single_attempt=True)
            if not isinstance(result.get("data"), list):
                raise APIError("protocol", 200)
        except APIError as exc:
            state.update(api="reachable" if exc.status else "unavailable", error=exc.kind)
            if exc.kind == "authentication":
                state["authentication"] = "invalid"
            elif exc.kind == "permission":
                state["authentication"] = "permission_denied"
        except CAEError as exc:
            state.update(error=exc.code)
        else:
            state.update(authentication="valid", api="available")
        state["checked_at"] = datetime.now(UTC).isoformat()
        with self._lock:
            self._health = state
        return self.get_status()

    def list_models(self) -> list[str]:
        result = self._broker.execute(self._app, self._profile, "models")
        data = result.get("data")
        if not isinstance(data, list) or any(
            not isinstance(x, dict) or not isinstance(x.get("id"), str) for x in data
        ):
            raise APIError("protocol")
        return [item["id"] for item in data]

    def create_response(
        self, model: str, input: str, *, max_output_tokens: int = 256
    ) -> dict[str, Any]:
        if not isinstance(model, str) or not 1 <= len(model) <= 128:
            raise ConfigurationError()
        if not isinstance(input, str) or not 1 <= len(input) <= 100_000:
            raise ConfigurationError()
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 32768:
            raise ConfigurationError()
        return self._broker.execute(
            self._app,
            self._profile,
            "responses",
            {
                "model": model,
                "input": input,
                "max_output_tokens": max_output_tokens,
                "store": False,
            },
        )
