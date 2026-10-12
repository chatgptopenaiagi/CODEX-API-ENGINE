import json
from unittest.mock import patch

import pytest
from test_application_registry import image
from test_broker_lifecycle import configuration

from cae.errors import AccessDenied, ConfigurationError
from cae.operator_view import OperatorView


def test_selection_pin_registration_and_revocation(tmp_path):
    config, _, _ = configuration(tmp_path)
    view = OperatorView(config)
    destination = tmp_path / "selection.json"
    view.remember(destination)
    restored = OperatorView.restore(destination)
    assert restored.applications()[0]["app"] == "test-admin"
    assert restored.register("sample", image(tmp_path))["permissions_granted"] is False
    assert restored.revoke("sample")["revoked"] is True
    with pytest.raises(FileExistsError):
        view.remember(destination)
    value = json.loads(config.read_text())
    value["server"]["sha256"] = "0" * 64
    config.write_text(json.dumps(value))
    with pytest.raises(ConfigurationError):
        view.applications()
    with pytest.raises(ConfigurationError):
        OperatorView.restore(destination)


def test_selection_admin_denial_and_fixed_status(tmp_path):
    config, _, _ = configuration(tmp_path)
    view = OperatorView(config)
    with patch("cae.operator_view.BrokerClient") as client:
        client.return_value.get_status.return_value = {"version": "synthetic"}
        assert view.status() == {"version": "synthetic"}
    value = json.loads(config.read_text())
    value["clients"][0]["admin"] = False
    config.write_text(json.dumps(value))
    with pytest.raises(AccessDenied):
        view.register("sample", image(tmp_path))
    with pytest.raises(AccessDenied):
        view.applications()
    assert not config.with_name("broker.apps.lock").exists()


@pytest.mark.parametrize("value", [{}, {"schema_version": True}, {"schema_version": 1, "configuration": "relative"}])
def test_malformed_selection(tmp_path, value):
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ConfigurationError):
        OperatorView.restore(path)


def test_unsafe_and_tampered_selection(tmp_path):
    with pytest.raises(ConfigurationError):
        OperatorView(tmp_path / "not-configuration.txt")
    config, _, _ = configuration(tmp_path)
    view = OperatorView(config)
    path = tmp_path / "selection.json"
    view.remember(path)
    original = path.read_text()
    for key in ("pipe", "runtime", "server"):
        data = json.loads(original)
        data[key] = "different"
        path.write_text(json.dumps(data))
        with pytest.raises(ConfigurationError):
            OperatorView.restore(path)
    path.write_bytes(b" " * 65537)
    with pytest.raises(ConfigurationError):
        OperatorView.restore(path)
