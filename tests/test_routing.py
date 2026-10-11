import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from test_ipc import broker as broker

from cae.access import AccessRuntime
from cae.audit import AuditLog
from cae.broker_client import BrokerRemoteError
from cae.config import load_runtime, parse_config
from cae.errors import (
    APIError,
    AuditError,
    ConcurrentLimitExceeded,
    ConfigurationError,
    QuotaExceeded,
)
from cae.policy import ROUTING_MODES, PolicyEngine, Rule
from cae.providers import ProviderConfig
from cae.routing import CapabilityRequest, RoutingError, validated_result


class Adapter:
    capabilities = frozenset({"chat", "embeddings", "models"})

    def __init__(self, name="local", kind="ollama", **kwargs):
        self.config = ProviderConfig(name, kind, authenticated=kind == "openai",
                                     routing_models=("sample",), **kwargs)
        self.calls = []
        self.failure = False
        self.result = {"text": "synthetic answer", "usage": {"reported": True,
                       "input_tokens": 2, "output_tokens": 3}}
        self.wait = None

    def request(self, operation, secret, model, text, max_tokens):
        self.calls.append((operation, model, text))
        if self.wait:
            self.wait[0].set()
            assert self.wait[1].wait(5)
        if self.failure:
            raise APIError("unavailable")
        return self.result


def rule(provider, **kwargs):
    return Rule(provider.config.name, "app", provider.config.name, "default",
                frozenset({"chat", "embeddings"}), models=frozenset({"sample"}),
                routing_modes=ROUTING_MODES, **kwargs)


def request(**kwargs):
    return dict(contract_version=1, capability="chat_generation", model="sample",
                input="private prompt", routing_mode="LOCAL_ONLY", **kwargs)


def routed(rt, **kwargs):
    data = request()
    data.update(kwargs)
    return rt.router.execute("app", data)


@pytest.fixture
def factory(store):
    instances = []
    store.write("default", "sk-" + "SyntheticRoutingTestOnly" * 3)

    def make(providers=None, rules=None, **kwargs):
        providers = tuple(providers or (Adapter(),))
        rt = AccessRuntime(providers, PolicyEngine(tuple(rules) if rules is not None else
                          tuple(rule(p) for p in providers)), stores=lambda _: store, **kwargs)
        instances.append(rt)
        return rt
    yield make
    for rt in instances:
        rt.close()


def test_local_modes_deterministic_authorized_correlation(factory, store):
    a, b, cloud = Adapter("a"), Adapter("b"), Adapter("cloud", "openai", routing_priority=0)
    rt = factory((b, cloud, a), (rule(a), rule(b), rule(cloud, allow_cloud=True, allow_fallback=True)))
    for mode in ("LOCAL_ONLY", "LOCAL_FIRST"):
        assert routed(rt, routing_mode=mode)["provider_id"] == "a"
    result = routed(rt, routing_mode="EXPLICIT_PROVIDER", provider="b")
    assert result["provider_id"] == "b" and result["usage"]["state"] == "CONFIRMED_USAGE"
    assert result["usage"]["input_tokens"] == 2
    assert routed(rt, routing_mode="CLOUD_ONLY")["provider_id"] == "cloud"
    assert len(cloud.calls) == 1 and store.reads == 1
    rows = rt.audit_log.events()
    assert "private prompt" not in json.dumps(rows)
    assert len({r["request_id"] for r in rows[-5:]}) == 1
    assert rows[-1]["outcome"] == "COMPLETED" and rows[-1]["model"] == "sample"
    assert rows[-1]["capability"] == "chat_generation"


@pytest.mark.parametrize("change", [
    {"contract_version": True}, {"contract_version": 2}, {"contract_version": None},
    {"capability": []}, {"model": "*"}, {"model": None}, {"model": "sk-synthetic-model-canary"}, {"input": ""},
    {"input": "x" * 8193}, {"input": {}}, {"input": "\ud800"},
    {"routing_mode": []}, {"routing_mode": "BAD"}, {"provider": "local"},
    {"routing_mode": "EXPLICIT_PROVIDER"}, {"routing_mode": "EXPLICIT_PROVIDER", "provider": "../x"},
    {"allow_fallback": True}, {"allow_fallback": 1}, {"max_tokens": True},
    {"max_tokens": 0}, {"max_tokens": 4097}, {"app": "admin"},
    {"endpoint": "https://example.invalid"}, {"credential": "private"}, {"input": ["x"]},
])
def test_malformed_before_any_dispatch(factory, store, change):
    rt = factory()
    with pytest.raises(ConfigurationError):
        routed(rt, **change)
    assert store.reads == 0 and not rt.router.providers[0].calls


def test_unknown_capability_and_missing_fields(factory):
    rt = factory()
    with pytest.raises(RoutingError, match="capability_unknown"):
        routed(rt, capability="moderation")
    with pytest.raises(ConfigurationError):
        CapabilityRequest.parse({"contract_version": 1, "capability": "chat_generation"})
    with pytest.raises(ConfigurationError):
        CapabilityRequest.parse([])
    assert str(RoutingError("raw private error")) == "routing_policy_denied"


@pytest.mark.parametrize("case", ["unenrolled", "provider", "model", "legacy", "cloud", "denied", "unsupported", "custom"])
def test_default_deny_and_intersections(factory, store, case):
    p = Adapter("cloud", "openai")
    grants = [rule(p, allow_cloud=case != "cloud")]
    data = {"routing_mode": "CLOUD_ONLY"}
    if case == "unenrolled":
        grants = [replace(grants[0], app="other")]
    if case == "provider":
        data.update(routing_mode="EXPLICIT_PROVIDER", provider="unknown")
    if case == "model":
        data["model"] = "alias"
    if case == "legacy":
        grants = [replace(grants[0], routing_modes=frozenset())]
    if case == "denied":
        grants.append(replace(grants[0], id="deny", effect="deny"))
    if case == "unsupported":
        p.capabilities = frozenset({"models"})
    if case == "custom":
        p.config = ProviderConfig("cloud", "custom", routing_models=("sample",))
    rt = factory((p,), grants)
    with pytest.raises(RoutingError, match="routing_policy_denied"):
        routed(rt, **data)
    assert not p.calls and store.reads == 0


def test_fallback_permission_disabled_and_recovery(factory):
    local, cloud = Adapter(routing_enabled=False), Adapter("cloud", "openai")
    rt = factory((local, cloud), (rule(local, allow_fallback=True), rule(cloud, allow_cloud=True)))
    with pytest.raises(RoutingError):
        routed(rt, routing_mode="LOCAL_FIRST", allow_fallback=True)
    with pytest.raises(RoutingError, match="provider_unavailable"):
        routed(rt, routing_mode="LOCAL_FIRST")
    cloud_rule = replace(rule(cloud), allow_cloud=True, allow_fallback=True)
    rt2 = factory((local, cloud), (rule(local, allow_fallback=True), cloud_rule))
    result = routed(rt2, routing_mode="LOCAL_FIRST", allow_fallback=True)
    assert result["provider_id"] == "cloud" and result["routing_metadata"]["fallback"] is True
    with pytest.raises(RoutingError):
        routed(rt2)
    assert not local.calls and len(cloud.calls) == 1


def test_unknown_outcome_never_replayed_cache_expires(factory):
    local, cloud = Adapter(), Adapter("cloud", "openai")
    rt = factory((local, cloud), (rule(local, allow_fallback=True),
                                  rule(cloud, allow_cloud=True, allow_fallback=True)))
    now = [100.0]
    rt.router.clock = lambda: now[0]
    local.failure = True
    with pytest.raises(RoutingError, match="request_outcome_unknown"):
        routed(rt, routing_mode="LOCAL_FIRST", allow_fallback=True)
    assert len(local.calls) == 1 and not cloud.calls
    assert routed(rt, routing_mode="LOCAL_FIRST", allow_fallback=True)["provider_id"] == "cloud"
    local.failure = False
    now[0] += 6
    assert routed(rt, routing_mode="LOCAL_FIRST", allow_fallback=True)["provider_id"] == "local"


def test_no_candidate_does_not_reserve_and_route_cannot_evade_quota(factory):
    p = Adapter()
    rt = factory((p,), (rule(p, max_requests_per_day=1),))
    with pytest.raises(RoutingError):
        routed(rt, model="denied")
    routed(rt)
    with pytest.raises(QuotaExceeded):
        routed(rt, routing_mode="EXPLICIT_PROVIDER", provider="local")
    assert len(p.calls) == 1


def test_concurrency_and_audit_failure_before_vault(factory, store, monkeypatch):
    p = Adapter("cloud", "openai")
    rt = factory((p,), (rule(p, allow_cloud=True, max_concurrent_requests=1),))
    entered, release = threading.Event(), threading.Event()
    p.wait = entered, release
    with ThreadPoolExecutor(2) as pool:
        job = pool.submit(routed, rt, routing_mode="CLOUD_ONLY")
        assert entered.wait(5)
        try:
            with pytest.raises(ConcurrentLimitExceeded):
                routed(rt, routing_mode="CLOUD_ONLY")
        finally:
            release.set()
        assert job.result()["provider_id"] == "cloud"
    assert len(p.calls) == store.reads == 1
    def broken(*args, **kwargs):
        raise AuditError()
    monkeypatch.setattr(rt.audit_log, "emit", broken)
    with pytest.raises(AuditError):
        routed(rt, routing_mode="CLOUD_ONLY")
    assert len(p.calls) == store.reads == 1


@pytest.mark.parametrize("value", [None, [], {"text": ""}, {"text": 1},
    {"text": "x" * 8193}, {"text": "x" * 49000}, {"text": "ok", "usage": []},
    {"text": "ok", "usage": {"reported": 1}},
    {"text": "ok", "usage": {"input_tokens": True}},
    {"text": "ok", "usage": {"output_tokens": -1}},
    {"text": "ok", "usage": {"output_tokens": 10**13}},
])
def test_untrusted_response_rejection(value):
    with pytest.raises(RoutingError, match="provider_response_invalid"):
        validated_result("chat_generation", value)


@pytest.mark.parametrize("vectors", [[], [[1], [2]], [[]], [[True]], [[float("nan")]], [[float("inf")]], [[1] * 4097], "bad"])
def test_embedding_bounds(vectors):
    with pytest.raises(RoutingError):
        validated_result("embeddings", {"vectors": vectors})


def test_embeddings_unknown_usage_and_invalid_after_dispatch(factory):
    p = Adapter()
    p.result = {"vectors": [[0.1, 0.2]]}
    rt = factory((p,))
    result = routed(rt, capability="embeddings")
    assert result["usage"]["state"] == "UNKNOWN_USAGE" and result["usage"]["input_tokens"] is None
    p.result = {"text": ""}
    with pytest.raises(RoutingError, match="request_outcome_unknown"):
        routed(rt)
    assert len(p.calls) == 2


def test_discovery_sanitized_and_real_pipe_extension(broker):
    server, client, store = broker
    assert client.capabilities()["capabilities"] == []
    p = server.runtime.router.providers[0]
    p.config = replace(p.config, routing_models=("safe-model",))
    server.runtime.policy.rules = tuple(replace(r, routing_modes=ROUTING_MODES, allow_cloud=True)
                                         for r in server.runtime.policy.rules)
    result = client.capabilities()
    assert {r["capability"] for r in result["capabilities"]} == {"chat_generation", "embeddings"}
    assert all("endpoint" not in row and "profile" not in row for row in result["capabilities"])
    response = client.route("chat_generation", "safe-model", "synthetic", routing_mode="CLOUD_ONLY")
    assert response["usage"]["state"] == "UNKNOWN_USAGE"
    assert "sk-" not in json.dumps(response)
    with pytest.raises(BrokerRemoteError, match="invalid_protocol"):
        client.request("capabilities", app="admin")
    with pytest.raises(BrokerRemoteError, match="routing_policy_denied"):
        client.route("chat_generation", "safe-model", "synthetic")


@pytest.mark.parametrize("kwargs", [
    {"routing_models": "x"}, {"routing_models": ["*"]}, {"routing_models": [1]},
    {"routing_models": ["x", "x"]}, {"routing_models": [str(i) for i in range(129)]},
    {"routing_priority": True}, {"routing_priority": -1}, {"routing_priority": 10001},
    {"routing_enabled": 1},
])
def test_invalid_provider_routing_configuration(kwargs):
    with pytest.raises(ConfigurationError):
        ProviderConfig("openai", "openai", **kwargs)


@pytest.mark.parametrize("kwargs", [{"routing_modes": "LOCAL_ONLY"}, {"routing_modes": [1]},
    {"routing_modes": ["BAD"]}, {"allow_cloud": 1}, {"allow_fallback": "true"}])
def test_invalid_grants(kwargs):
    with pytest.raises(ConfigurationError):
        replace(rule(Adapter()), **kwargs)


def test_config_opt_in_and_legacy_loading(tmp_path):
    text = '''schema_version=1
[[providers]]
name="local"
kind="ollama"
authenticated=false
routing_models=["sample"]
[[rules]]
id="local"
app="app"
provider="local"
profile="default"
operations=["chat"]
models=["sample"]
routing_modes=["LOCAL_ONLY"]
'''
    path = tmp_path / "runtime.toml"
    path.write_text(text)
    rt = load_runtime(path)
    try:
        assert rt.router.discover("app")["capabilities"][0]["model_id"] == "sample"
    finally:
        rt.close()
    providers, rules = parse_config(text.replace('routing_models=["sample"]', "").replace('routing_modes=["LOCAL_ONLY"]', ""))
    assert providers[0].routing_models == () and not rules[0].routing_modes


def test_failed_cache_bound_and_discovery_unavailable(factory):
    p = Adapter()
    rt = factory((p,))
    rt.router.clock = lambda: 10
    rt.router._failed = {("app", str(i), "sample"): 15 for i in range(1024)}
    p.failure = True
    with pytest.raises(RoutingError):
        routed(rt)
    assert len(rt.router._failed) == 1024
    assert rt.router.discover("app")["capabilities"][0]["availability"] == "UNAVAILABLE"


def test_usage_partial_never_claimed_confirmed():
    result, usage = validated_result("chat_generation", {"text": "ok", "usage": {"reported": True, "input_tokens": 2}})
    assert usage["state"] == "UNKNOWN_USAGE" and result == {"text": "ok"}
    result, usage = validated_result("embeddings", {"vectors": [[1]], "usage": {"reported": True, "input_tokens": 2}})
    assert usage["state"] == "CONFIRMED_USAGE" and usage["output_tokens"] is None


def test_managed_audit_routing_rotates_and_preserves_correlation(factory, tmp_path):
    from cae.audit_storage import Retention
    audit = AuditLog(tmp_path / "managed" / "active.jsonl", retention=Retention(active_bytes=4096, total_bytes=8192))
    rt = factory(audit=audit)
    for _ in range(10):
        routed(rt)
    rows = audit.events(include_archives=True)
    assert rows[-1]["event"] == "route_completed"
    assert len({r["request_id"] for r in rows[-5:]}) == 1
    assert audit.storage_status()["health"] == "ready"
    assert "private prompt" not in json.dumps(rows)


@pytest.mark.parametrize("field,value", [("capability", "unknown"), ("routing_mode", "bad"),
    ("model", "../bad model"), ("outcome", "raw error"), ("fallback", 1)])
def test_audit_metadata_is_strict(field, value):
    from cae.audit import AuditEvent
    row = AuditLog().emit("broker_status").to_dict()
    row[field] = value
    with pytest.raises(ValueError):
        AuditEvent(**row).validate()


def test_recent_success_observation_and_bounded_memory(factory):
    rt = factory()
    now = [20]
    rt.router.clock = lambda: now[0]
    rt.router._succeeded = {("app", str(i), "sample"): 25 for i in range(1024)}
    routed(rt)
    assert len(rt.router._succeeded) == 1024
    discovery = rt.router.discover("app")
    assert discovery["capabilities"][0]["availability"] == "AVAILABLE"
    assert discovery["contracts"]["chat_generation"]["schema_version"] == 1
    now[0] = 26
    assert rt.router.discover("app")["capabilities"][0]["availability"] == "UNKNOWN"
    assert rt.router.discover("denied")["capabilities"] == []


def test_routed_quota_persists_restart(tmp_path):
    from cae.policy import QuotaLedger
    p = Adapter()
    for iteration in range(2):
        rt = AccessRuntime((p,), PolicyEngine((rule(p, max_requests_per_day=1),),
                           QuotaLedger(tmp_path / "quota.sqlite")))
        try:
            if iteration == 0:
                routed(rt)
            else:
                with pytest.raises(QuotaExceeded):
                    routed(rt, routing_mode="LOCAL_FIRST")
        finally:
            rt.close()
    assert len(p.calls) == 1


@pytest.mark.parametrize("data", [
    {"model": "wrong", "output": []}, {"status": "incomplete", "output": []},
    {"model": [], "output": []}, {"status": 3, "output": []},
])
def test_provider_model_and_completion_status_validation(data):
    from test_access_platform import Transport

    from cae.providers import HTTPProvider
    p = HTTPProvider(ProviderConfig("openai", "openai"), Transport(data))
    with pytest.raises(APIError):
        p.request("chat", "synthetic", "sample", "test")


def test_discovery_truncation_and_explicit_no_substitution(factory):
    p, alternative = Adapter(routing_enabled=False), Adapter("alternative")
    rt = factory((p, alternative))
    with pytest.raises(RoutingError, match="provider_unavailable"):
        routed(rt, routing_mode="EXPLICIT_PROVIDER", provider="local")
    assert not alternative.calls
    models = tuple("model-" + str(i) for i in range(80))
    p.config = replace(p.config, routing_models=models)
    rt.policy.rules = (replace(rule(p), models=frozenset(models)),)
    result = rt.router.discover("app")
    assert result["truncated"] and len(result["capabilities"]) == 64


def test_registry_update_preserves_operator_routing_grants(tmp_path, monkeypatch):
    # Serialize existing rules through the actual administrative update path.
    import os

    from cae.ipc_protocol import BrokerSettings, Enrollment
    from cae.pipe_transport import process_peer
    from cae.registry import ApplicationRegistry
    peer = process_peer(os.getpid())
    runtime = tmp_path / "runtime.toml"
    runtime.write_text('''schema_version=1
[[providers]]
name="local"
kind="ollama"
authenticated=false
routing_models=["sample"]
[[rules]]
id="retained"
app="app"
provider="local"
profile="default"
operations=["chat"]
models=["sample"]
routing_modes=["LOCAL_FIRST"]
allow_fallback=true
''')
    admin = Enrollment("admin", peer.image, peer.sha256, True)
    app = Enrollment("app", str(tmp_path / "synthetic.exe"), "0" * 64)
    settings = BrokerSettings("cae-unit", runtime, admin, (admin, app))
    monkeypatch.setattr(BrokerSettings, "load", lambda _: settings)
    registry = ApplicationRegistry(tmp_path / "broker.json")
    registry.authorize("app", "local", "default", frozenset({"chat"}), models=frozenset({"sample"}))
    providers, rules = parse_config(runtime.read_text())
    assert providers[0].routing_models == ("sample",)
    assert rules[0].id == "retained" and rules[0].routing_modes == frozenset({"LOCAL_FIRST"})
    assert rules[0].allow_fallback


@pytest.mark.parametrize("payload", [None, [], "private provider text"])
def test_nondictionary_adapter_output_is_unknown_without_retry(factory, payload):
    p = Adapter()
    p.result = payload
    rt = factory((p,))
    with pytest.raises(RoutingError, match="request_outcome_unknown"):
        routed(rt)
    assert len(p.calls) == 1
