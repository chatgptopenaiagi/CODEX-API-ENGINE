"""Client facade tests; transport security remains covered by native IPC tests."""

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from cae import CAEError

SOURCE = Path(__file__).resolve().parents[1] / "clients/python/src/cae_client/__init__.py"
spec = importlib.util.spec_from_file_location("cae_client", SOURCE)
assert spec and spec.loader
client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_module)


class FakeClient:
    def __init__(self, **kwargs: Any) -> None:
        self.settings = kwargs

    def request(self, operation: str, **kwargs: Any) -> dict[str, Any]:
        return {"operation": operation, **kwargs}

    def health(self, provider: str, profile: str) -> dict[str, Any]:
        return self.request("health", provider=provider, profile=profile)

    def list_models(self, provider: str, profile: str) -> dict[str, Any]:
        return self.request("models", provider=provider, profile=profile)

    def diagnostics(self, provider: str, profile: str) -> dict[str, Any]:
        return self.request("diagnostics", provider=provider, profile=profile)


def test_facade_uses_only_public_sdk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "BrokerClient", FakeClient)
    path = tmp_path / "client.json"
    path.write_text(json.dumps({"pipe": "cae-test", "server_image": "C:/CAE/Broker.exe",
                                "server_sha256": "0" * 64}), encoding="utf-8")
    monkeypatch.setenv("CAE_CONNECTION_FILE", str(path))
    client = client_module.CAEClient()
    assert client.connect() == {"operation": "status"}
    assert client.health("local")["provider"] == "local"
    assert client.models()["operation"] == "models"
    assert client.capabilities("test")["profile"] == "test"
    assert client.diagnostics()["operation"] == "diagnostics"


@pytest.mark.parametrize("text", ["{}", "[]", "null", '{"pipe":1,"pipe":2}', "x" * 65537],
                         ids=["empty", "array", "null", "duplicate", "oversized"])
def test_invalid_descriptor_is_sanitized(text: str, tmp_path: Path) -> None:
    path = tmp_path / "client.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(CAEError) as error:
        client_module.CAEClient(path)
    assert str(error.value) == "engine_error"


def test_no_implicit_current_directory_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CAE_CONNECTION_FILE", raising=False)
    with pytest.raises(CAEError):
        client_module.CAEClient()
