"""Versioned, secret-free application SDK."""

from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from .access import AccessRuntime
from .broker import Broker
from .errors import APIError, CAEError, ConfigurationError
from .security import identifier
from .version import __version__


class CAE:
    def __init__(
        self,
        profile: str = "default",
        *,
        app: str = "cae-console",
        broker: Broker | None = None,
        config: Path | None = None,
        runtime: AccessRuntime | None = None,
        provider: str = "openai",
    ) -> None:
        self._profile = identifier(profile)
        self._app = identifier(app)
        self._provider_name = identifier(provider)
        if config is not None and runtime is not None:
            raise ConfigurationError()
        if config is not None:
            from .config import load_runtime

            runtime = load_runtime(config)
        if broker is not None and runtime is not None:
            raise ConfigurationError()
        self._access = (
            runtime
            if runtime is not None
            else AccessRuntime.default(profile)
            if broker is None
            else None
        )
        self._broker = broker
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
        if self._access is not None:
            report = self.health()
            configured = report["credential"] in {"stored", "not_required"}
            return {
                "sdk_version": __version__,
                "schema_version": 2,
                "configured": configured,
                "engine": "ready" if configured else "not_configured",
                **report,
            }
        credential = "missing"
        broker_status = "ready"
        try:
            assert self._broker is not None
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
        if self._access is not None:
            return {"sdk_version": __version__, "schema_version": 2, **self.connect()}
        state: dict[str, Any] = {"authentication": "unknown", "api": "unknown", "error": None}
        try:
            assert self._broker is not None
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
        if self._access is not None:
            return self.models()
        assert self._broker is not None
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
        if self._access is not None:
            return self.provider(self._provider_name).chat(
                model, input, max_output_tokens=max_output_tokens
            )
        assert self._broker is not None
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

    def _runtime(self) -> AccessRuntime:
        if self._access is None:
            raise ConfigurationError()
        return self._access

    def provider(self, name: str) -> ProviderSession:
        return ProviderSession(self._runtime(), self._app, identifier(name), self._profile)

    def connect(self, provider: str | None = None) -> dict[str, Any]:
        return self.provider(provider or self._provider_name).health(probe=True)

    def health(self) -> dict[str, Any]:
        return self.provider(self._provider_name).health()

    def diagnostics(self) -> dict[str, Any]:
        return {
            "sdk_version": __version__,
            "schema_version": 2,
            "health": self.health(),
            "providers": self.providers(),
            "policy_rules": len(self.policies()),
            "isolation": "trusted_host_in_process",
        }

    def providers(self) -> list[dict[str, Any]]:
        return self._runtime().providers(self._app, self._profile)

    def models(self, provider: str | None = None) -> list[str]:
        return self.provider(provider or self._provider_name).list_models()

    def policies(self) -> list[dict[str, Any]]:
        return self._runtime().policies(self._app)

    def audit(self) -> list[dict[str, Any]]:
        return self._runtime().audit(self._app)

    def close(self) -> None:
        if self._access is not None:
            self._access.close()


class ProviderSession:
    """Secret-free application capability surface; no endpoint/policy mutation methods."""

    def __init__(self, runtime: AccessRuntime, app: str, name: str, profile: str) -> None:
        self._runtime = runtime
        self._app, self._name, self._profile = app, name, profile

    def list_models(self) -> list[str]:
        result = self._runtime.execute(self._app, self._name, self._profile, "models")
        models: list[str] = result["models"]
        return models

    def chat(self, model: str, input: str, *, max_output_tokens: int = 256) -> dict[str, Any]:
        return self._runtime.execute(
            self._app,
            self._name,
            self._profile,
            "chat",
            model=model,
            text=input,
            max_tokens=max_output_tokens,
        )

    def embeddings(self, model: str, input: str) -> dict[str, Any]:
        return self._runtime.execute(
            self._app, self._name, self._profile, "embeddings", model=model, text=input
        )

    def health(self, *, probe: bool = False) -> dict[str, Any]:
        return self._runtime.health(self._app, self._name, self._profile, probe=probe)

    def diagnostics(self) -> dict[str, Any]:
        return self.health()

    def usage(self) -> dict[str, Any]:
        return self._runtime.usage(self._app, self._name, self._profile)
