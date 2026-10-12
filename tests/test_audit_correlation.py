import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_access_platform import runtime
from test_ipc import broker as broker

from cae.audit import AuditLog, request_scope
from cae.broker_client import BrokerRemoteError
from cae.errors import AuditError, QuotaExceeded


def test_scope_nesting_failure_cleanup_and_legacy_events():
    audit = AuditLog()
    with pytest.raises(RuntimeError), request_scope() as first:
        with request_scope() as nested:
            assert first == nested
            audit.emit("policy_granted", app="sample")
        raise RuntimeError("synthetic private message")
    assert audit.emit("broker_status").request_id == ""
    with request_scope() as second:
        assert second != first
        audit.emit("request_completed")
    rows = audit.events()
    assert rows[0]["decision"] == "allow"
    assert rows[0]["request_id"] == first
    assert rows[2]["request_id"] == second
    assert rows[2]["latency_ms"] >= 0
    assert "synthetic private message" not in json.dumps(rows)


def test_threads_do_not_cross_correlate():
    audit = AuditLog()
    barrier = threading.Barrier(8)

    def work(index):
        with request_scope() as correlation:
            barrier.wait(timeout=5)
            audit.emit("policy_granted", app=f"app-{index}")
            audit.emit("request_completed", app=f"app-{index}")
            return correlation

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(work, range(8)))
    assert len(set(ids)) == 8
    for index, correlation in enumerate(ids):
        rows = audit.events(app=f"app-{index}")
        assert len(rows) == 2
        assert {row["request_id"] for row in rows} == {correlation}
        assert rows[1]["latency_ms"] >= rows[0]["latency_ms"]


def test_legacy_jsonl_remains_readable(tmp_path):
    path = tmp_path / "audit.jsonl"
    row = AuditLog().emit("broker_status").to_dict()
    for field in ("request_id", "decision", "status", "error_code", "latency_ms"):
        row.pop(field)
    path.write_text(json.dumps(row) + "\n")
    result = AuditLog(path).events()[0]
    assert result["request_id"] == "" and result["latency_ms"] is None
    assert result["status"] == "none"


@pytest.mark.parametrize("field,value", [
    ("request_id", False), ("request_id", "client-controlled"), ("request_id", "a" * 31),
    ("decision", "privileged"), ("status", "arbitrary body"),
    ("error_code", "Bearer synthetic-sensitive"),
    ("latency_ms", True), ("latency_ms", -1), ("latency_ms", float("inf")),
    ("latency_ms", float("nan")), ("latency_ms", "bad"),
])
def test_invalid_metadata_rejected_without_echo(tmp_path, field, value):
    path = tmp_path / "audit.jsonl"
    row = AuditLog().emit("broker_status").to_dict()
    row[field] = value
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(AuditError) as error:
        AuditLog(path).events()
    assert str(error.value) == "audit_unavailable"


def test_unknown_error_code_is_not_persisted(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    row = audit.emit("request_failed", error_code="private-provider-error").to_dict()
    assert row["error_code"] == "engine_error" and row["status"] == "error"
    assert "private-provider-error" not in audit._path.read_text()


def test_direct_runtime_grant_result_and_quota_denial(store):
    engine, access, transport = runtime(store, limit=1)
    try:
        engine.models()
        reads, calls = store.reads, len(transport.calls)
        with pytest.raises(QuotaExceeded):
            engine.models()
        rows = access.audit_log.events()
        assert len({row["request_id"] for row in rows[:3]}) == 1
        assert rows[0]["request_id"] and rows[-1]["request_id"] != rows[0]["request_id"]
        assert rows[-1]["decision"] == "deny"
        assert rows[-1]["error_code"] == "daily_request_limit"
        assert store.reads == reads and len(transport.calls) == calls
    finally:
        engine.close()


def test_real_pipe_auth_policy_result_correlation(broker):
    server, client, store = broker
    client.list_models()
    rows = [row for row in server.runtime.audit_log.events() if row["app"] == "client-a"]
    assert [row["event"] for row in rows] == [
        "ipc_authenticated", "policy_granted", "request_completed",
        "provider_connected", "ipc_result",
    ]
    assert len({row["request_id"] for row in rows}) == 1
    assert rows[0]["request_id"]
    assert rows[-1]["latency_ms"] >= rows[0]["latency_ms"]
    reads = store.reads
    with pytest.raises(BrokerRemoteError):
        client.request("stop")
    denied = server.runtime.audit_log.events()[-1]
    assert denied["event"] == "ipc_denied" and denied["decision"] == "deny"
    assert denied["error_code"] == "access_denied"
    assert store.reads == reads and denied["request_id"] != rows[0]["request_id"]


def test_broker_audit_failure_returns_fixed_error_without_provider_io(broker, monkeypatch):
    server, client, store = broker

    def broken(*args, **kwargs):
        raise AuditError()

    monkeypatch.setattr(server.runtime.audit_log, "emit", broken)
    with pytest.raises(BrokerRemoteError) as error:
        client.list_models()
    assert error.value.code == "audit_unavailable"
    assert store.reads == 0
