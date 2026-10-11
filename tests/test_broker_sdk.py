import json

import pytest
from conftest import FAKE_KEY, FakeTransport

from cae import CAE
from cae.api import OpenAIConnector
from cae.broker import Broker, Grant
from cae.errors import AccessDenied, APIError, ConfigurationError, CredentialError
from cae.monitor import HealthMonitor


def make_engine(store, replies=None, operations=frozenset({"models"})):
    store.write("default", FAKE_KEY)
    transport = FakeTransport(replies)
    broker = Broker(
        store, (Grant("demo", "default", operations),), OpenAIConnector(transport, retries=0)
    )
    return CAE(app="demo", broker=broker), broker, transport


def test_success_status_and_offline_snapshot(store):
    engine, broker, transport = make_engine(store)
    assert engine.configure()["authentication"] == "unknown"
    assert not transport.calls
    status = engine.test_connection()
    assert status["authentication"] == "valid"
    assert status["api"] == "available"
    assert len(transport.calls) == 1
    assert engine.get_status() == status
    assert FAKE_KEY not in json.dumps(status)
    assert broker.audit()[0]["outcome"] == "success"


@pytest.mark.parametrize(
    "status,auth,api",
    [
        (401, "invalid", "reachable"),
        (403, "permission_denied", "reachable"),
        (429, "unknown", "reachable"),
        (503, "unknown", "reachable"),
    ],
)
def test_health_failure_classification(store, status, auth, api):
    engine, _, _ = make_engine(store, [(status, b"never disclose")])
    report = engine.test_connection()
    assert report["authentication"] == auth
    assert report["api"] == api


def test_network_failure_and_bad_schema(store):
    engine, _, _ = make_engine(store, [OSError(FAKE_KEY)])
    assert engine.test_connection()["api"] == "unavailable"
    engine, _, _ = make_engine(store, [(200, b"{}")])
    assert engine.test_connection()["error"] == "protocol"


@pytest.mark.parametrize(
    "app,profile,op",
    [
        ("other", "default", "models"),
        ("demo", "other", "models"),
        ("demo", "default", "responses"),
        ("demo", "default", "export"),
    ],
)
def test_deny_before_read(store, app, profile, op):
    _, broker, transport = make_engine(store)
    with pytest.raises(AccessDenied):
        broker.execute(app, profile, op)
    assert store.reads == 0
    assert not transport.calls
    assert broker.audit()[0]["outcome"] == "denied"


def test_grants_immutable_and_invalid():
    operations = {"models"}
    grant = Grant("app", "default", operations)
    operations.add("responses")
    assert grant.operations == frozenset({"models"})
    with pytest.raises(AccessDenied):
        Grant("app", "default", frozenset({"export"}))


def test_storage_errors_sanitized(store):
    engine, broker, _ = make_engine(store)

    def broken(_):
        raise RuntimeError(FAKE_KEY)

    store.read = broken
    with pytest.raises(CredentialError) as exc:
        broker.execute("demo", "default", "models")
    assert exc.value.__context__ is None
    assert engine.test_connection()["error"] == "credential_operation_failed"


def test_generation_explicit_and_bounded(store):
    engine, _, transport = make_engine(
        store, [(200, b'{"output":[],"usage":{"total_tokens":3}}')], frozenset({"responses"})
    )
    response = engine.create_response("test-model", "Hello", max_output_tokens=16)
    assert response["usage"]["total_tokens"] == 3
    assert transport.calls[0][2]["store"] is False
    for kwargs in (
        {"model": "", "input": "ok"},
        {"model": "x", "input": ""},
        {"model": "x", "input": "ok", "max_output_tokens": True},
    ):
        with pytest.raises(ConfigurationError):
            engine.create_response(**kwargs)


def test_models_schema(store):
    engine, _, _ = make_engine(store)
    assert engine.list_models() == ["model-for-test"]
    engine, _, _ = make_engine(store, [(200, b'{"data":[{}]}')])
    with pytest.raises(APIError):
        engine.list_models()


def test_denied_status_does_not_probe(store):
    broker = Broker(store, ())
    engine = CAE(app="other", broker=broker)
    assert engine.get_status()["broker"] == "denied_or_unavailable"
    assert not store.reads


def test_monitor_explicit_poll_and_stop(store):
    engine, _, transport = make_engine(store)
    monitor = HealthMonitor(engine, interval=30)
    assert monitor.snapshot()["authentication"] == "unknown"
    assert not transport.calls
    with monitor:
        monitor.start()
        monitor.stop()
    assert not monitor._thread.is_alive()
    assert len(transport.calls) == 1
    with pytest.raises(ConfigurationError):
        HealthMonitor(engine, interval=1)


def test_audit_bounded_and_copied(store):
    broker = Broker(store, ())
    for _ in range(110):
        with pytest.raises(AccessDenied):
            broker.execute("app", "default", "models")
    assert len(broker.audit()) == 100
    broker.audit()[0]["outcome"] = "tampered"
    assert broker.audit()[0]["outcome"] == "denied"
