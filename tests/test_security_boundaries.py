import json
from dataclasses import replace

import pytest
from test_access_platform import runtime
from test_ipc import broker as broker

from cae import CAE
from cae.access import AccessRuntime
from cae.api import OpenAIConnector
from cae.audit import AuditLog
from cae.broker import Broker
from cae.broker_client import BrokerRemoteError
from cae.config import load_runtime, parse_config
from cae.errors import AccessDenied, AuditError, ConfigurationError
from cae.ipc_protocol import encode
from cae.pipe_transport import ProtocolError
from cae.policy import PolicyEngine, Rule

PROVIDER = '\n[[providers]]\nname="local"\nkind="ollama"\nauthenticated=false\n'
RULE = ('\n[[rules]]\nid="test"\napp="app"\nprovider="local"\nprofile="default"\n'
        'operations=["models"]\n')


def test_legacy_connector_rejects_unlisted_routes():
    with pytest.raises(ConfigurationError):
        OpenAIConnector().request("synthetic-test-only", "credentials.export")


def test_public_sdk_configuration_is_explicit_and_unambiguous(tmp_path, store):
    config = tmp_path / "policy.toml"
    config.write_text("schema_version=1" + PROVIDER + RULE)
    configured = CAE(app="app", config=config, provider="local")
    try:
        assert configured.providers()[0]["name"] == "local"
    finally:
        configured.close()
    engine, access, _ = runtime(store)
    try:
        with pytest.raises(ConfigurationError):
            CAE(config=config, runtime=access)
        with pytest.raises(ConfigurationError):
            CAE(broker=Broker(store, ()), runtime=access)
    finally:
        engine.close()


@pytest.mark.parametrize("text", [
    "schema_version=true" + PROVIDER,
    "schema_version=1" + PROVIDER.replace("authenticated=false", 'authenticated="false"'),
    "schema_version=1" + PROVIDER + PROVIDER,
    "schema_version=1" + PROVIDER + RULE.replace('operations=["models"]', 'operations="models"'),
    "schema_version=1" + PROVIDER + RULE + RULE,
    "schema_version=1" + PROVIDER + RULE.replace('provider="local"', 'provider="missing"'),
])
def test_invalid_policy_configuration_fails_closed(text):
    with pytest.raises(ConfigurationError):
        parse_config(text)


def test_missing_configuration_does_not_fall_back_to_default(tmp_path):
    with pytest.raises(ConfigurationError):
        load_runtime(tmp_path / "missing.toml")


@pytest.mark.parametrize("field,value", [
    ("event", "not_an_allowed_event"), ("event_id", "bad"), ("timestamp", "not-a-date"),
])
def test_corrupt_audit_metadata_is_not_returned(tmp_path, field, value):
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(path)
    row = audit.emit("broker_status").to_dict()
    row[field] = value
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(AuditError) as error:
        audit.events()
    assert str(error.value) == "audit_unavailable"


def test_audit_input_and_symlink_guards(tmp_path):
    with pytest.raises(ConfigurationError):
        AuditLog(capacity=0)
    with pytest.raises(ConfigurationError):
        AuditLog().emit("unrecognized_event")
    target = tmp_path / "target.txt"
    target.write_text("unchanged")
    link = tmp_path / "alias.jsonl"
    link.symlink_to(target)
    with pytest.raises(AuditError):
        AuditLog(link).emit("broker_status")
    assert target.read_text() == "unchanged"


def test_runtime_unknown_provider_and_empty_generation_are_denied(store):
    engine, access, _ = runtime(store)
    try:
        provider = next(iter(access._providers.values()))
        with pytest.raises(ConfigurationError):
            AccessRuntime((provider, provider), access.policy)
        with pytest.raises(ConfigurationError):
            access.execute("app", "openai", "default", "chat", model="test-model", text="")
        assert store.reads == 0
        old = access.policy
        access.policy = PolicyEngine((Rule("missing", "app", "missing", "default",
                                          frozenset({"models"})),))
        old.ledger.close()
        with pytest.raises(AccessDenied):
            access.execute("app", "missing", "default", "models")
        assert store.reads == 0
    finally:
        engine.close()


def test_credential_presence_failure_is_fixed_metadata(store, monkeypatch):
    engine, _, _ = runtime(store)
    def broken(profile):
        raise RuntimeError("synthetic backend error")
    monkeypatch.setattr(store, "exists", broken)
    try:
        assert engine.health()["credential"] == "unavailable"
    finally:
        engine.close()


@pytest.mark.parametrize("failure", ["oversize", "unexpected", "typed", "ack"])
def test_broker_error_boundaries_never_echo_exceptions(broker, monkeypatch, failure):
    server, _, store = broker

    class Session:
        response = None
        received = 0

        def receive(self, timeout):
            self.received += 1
            if self.received == 1:
                return encode({"v": 1, "id": "a" * 32, "op": "status", "args": {}})
            return b"bad" if failure == "ack" else b"OK"

        def peer(self):
            return server.identity

        def send(self, value):
            self.response = json.loads(value)

    def dispatch(*args):
        if failure == "oversize":
            return {"huge": "a" * 65537}
        if failure == "unexpected":
            raise RuntimeError("must_not_be_disclosed")
        if failure == "typed":
            raise AccessDenied()
        return {}

    monkeypatch.setattr(server, "dispatch", dispatch)
    session = Session()
    if failure == "ack":
        with pytest.raises(ProtocolError):
            server._session(session)
    else:
        server._session(session)
        assert session.response["error"] == {
            "oversize": "invalid_protocol", "unexpected": "broker_unavailable", "typed": "access_denied",
        }[failure]
    assert "must_not_be_disclosed" not in json.dumps(session.response)
    assert store.reads == 0


def test_reload_cannot_silently_change_runtime_or_server(broker, tmp_path, monkeypatch):
    server, client, store = broker
    server.configuration = tmp_path / "broker.json"
    monkeypatch.setattr("cae.broker_service.BrokerSettings.load", lambda _: replace(
        server.settings, pipe="cae-another"))
    with pytest.raises(BrokerRemoteError, match="access_denied"):
        client.get_status()
    assert store.reads == 0
