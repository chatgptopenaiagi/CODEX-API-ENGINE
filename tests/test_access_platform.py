import concurrent.futures
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from conftest import FAKE_KEY

from cae import CAE
from cae.access import AccessRuntime
from cae.audit import AuditLog
from cae.config import load_runtime, parse_config
from cae.errors import (
    AccessDenied,
    APIError,
    AuditError,
    ConfigurationError,
    QuotaExceeded,
    UnsupportedOperation,
)
from cae.integrations import snapshot
from cae.policy import PolicyEngine, QuotaLedger, Rule
from cae.providers import HTTPProvider, HTTPProviderTransport, ProviderConfig


class Transport:
    def __init__(self, data, status=200):
        self.data, self.status, self.calls = data, status, []

    def send(self, config, method, path, headers, payload):
        self.calls.append((method, path, headers, payload))
        if isinstance(self.data, Exception):
            raise self.data
        return self.status, json.dumps(self.data).encode()


def config(kind):
    return ProviderConfig(
        kind,
        kind,
        endpoint="https://test.openai.azure.com" if kind == "azure-openai" else "",
        authenticated=kind not in {"ollama", "lmstudio", "vllm"},
    )


def runtime(store, *, kind="openai", data=None, operations=None, limit=10, audit=None):
    spec = config(kind)
    transport = Transport(data if data is not None else {"data": [{"id": "test-model"}]})
    provider = HTTPProvider(spec, transport)
    store.write("default", FAKE_KEY)
    rules = (
        Rule(
            "test-rule",
            "app",
            kind,
            "default",
            frozenset(
                operations or {"models", "health", "diagnostics", "chat", "embeddings", "usage"}
            ),
            models=frozenset({"test-model"}),
            max_requests_per_day=limit,
        ),
    )
    access = AccessRuntime((provider,), PolicyEngine(rules), stores=lambda _: store, audit=audit)
    return CAE(app="app", provider=kind, runtime=access), access, transport


@pytest.mark.parametrize(
    "kind", ["openai", "azure-openai", "anthropic", "gemini", "ollama", "vllm", "lmstudio"]
)
def test_models_all_providers(kind):
    rows = (
        {"models": [{"name": "models/test-model" if kind == "gemini" else "test-model"}]}
        if kind in {"gemini", "ollama"}
        else {"data": [{"id": "test-model"}]}
    )
    transport = Transport(rows)
    result = HTTPProvider(config(kind), transport).request("models", FAKE_KEY)
    assert result["models"] == ["test-model"]
    method, path, headers, payload = transport.calls[0]
    assert method == "GET" and payload is None
    assert ("?key=" not in path) and (FAKE_KEY not in path)
    if kind == "anthropic":
        assert headers["x-api-key"] == FAKE_KEY and headers["anthropic-version"] == "2023-06-01"
    if kind == "gemini":
        assert headers["x-goog-api-key"] == FAKE_KEY
    if kind in {"ollama", "vllm", "lmstudio"}:
        assert not headers


@pytest.mark.parametrize(
    "kind,data,route",
    [
        (
            "openai",
            {
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": "answer"}]}
                ]
            },
            "/v1/responses",
        ),
        (
            "azure-openai",
            {"choices": [{"message": {"content": "answer"}}]},
            "/openai/v1/chat/completions",
        ),
        ("anthropic", {"content": [{"type": "text", "text": "answer"}]}, "/v1/messages"),
        (
            "gemini",
            {
                "candidates": [{"content": {"parts": [{"text": "answer"}]}}],
                "usageMetadata": {"promptTokenCount": 3},
            },
            "/v1beta/models/test-model:generateContent",
        ),
        ("ollama", {"message": {"content": "answer"}, "prompt_eval_count": 3}, "/api/chat"),
        ("vllm", {"choices": [{"message": {"content": "answer"}}]}, "/v1/chat/completions"),
        ("lmstudio", {"choices": [{"message": {"content": "answer"}}]}, "/v1/chat/completions"),
    ],
)
def test_chat_contracts(kind, data, route):
    transport = Transport(data)
    result = HTTPProvider(config(kind), transport).request(
        "chat", FAKE_KEY, "test-model", "hello", 32
    )
    assert result["text"] == "answer"
    assert transport.calls[0][0:2] == ("POST", route)
    assert "usage" in result


@pytest.mark.parametrize("kind", ["openai", "azure-openai", "gemini", "ollama", "vllm", "lmstudio"])
def test_embeddings_contracts(kind):
    data = (
        {"embedding": {"values": [0.1, 0.2]}}
        if kind == "gemini"
        else {"embeddings": [[0.1, 0.2]]}
        if kind == "ollama"
        else {"data": [{"embedding": [0.1, 0.2]}]}
    )
    assert HTTPProvider(config(kind), Transport(data)).request(
        "embeddings", FAKE_KEY, "test-model", "hello"
    )["vectors"] == [[0.1, 0.2]]


@pytest.mark.parametrize(
    "kind,endpoint",
    [
        ("openai", "https://evil.invalid"),
        ("anthropic", "http://api.anthropic.com"),
        ("azure-openai", "https://x.openai.azure.com.evil.invalid"),
        ("ollama", "http://localhost:11434"),
        ("vllm", "http://192.168.1.1:8000"),
        ("lmstudio", "http://127.0.0.1:1234?key=oops"),
        ("ollama", "http://user:pass@127.0.0.1:11434"),
        ("unknown", ""),
    ],
)
def test_endpoint_exfiltration_rejected(kind, endpoint):
    with pytest.raises(ConfigurationError):
        ProviderConfig(
            "test", kind, endpoint, authenticated=kind not in {"ollama", "vllm", "lmstudio"}
        )


@pytest.mark.parametrize(
    "data,status,kind",
    [
        ({"error": FAKE_KEY}, 401, "authentication"),
        ({}, 403, "permission"),
        ({}, 429, "rate_limit"),
        ({}, 503, "unavailable"),
        ({}, 302, "request"),
        (RuntimeError(FAKE_KEY), 200, "unavailable"),
        ([], 200, "protocol"),
    ],
)
def test_safe_provider_failure(data, status, kind):
    transport = Transport(data, status)
    with pytest.raises(APIError) as error:
        HTTPProvider(config("openai"), transport).request("models", FAKE_KEY)
    assert error.value.kind == kind and error.value.__context__ is None
    assert FAKE_KEY not in str(error.value)
    assert len(transport.calls) == 1


def test_protocol_redaction_and_unsupported():
    provider = HTTPProvider(
        config("openai"),
        Transport(
            {
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": FAKE_KEY}]}
                ]
            }
        ),
    )
    assert FAKE_KEY not in json.dumps(provider.request("chat", FAKE_KEY, "test-model", "hello"))
    with pytest.raises(UnsupportedOperation):
        HTTPProvider(config("anthropic")).request("embeddings", FAKE_KEY, "x", "hello")
    with pytest.raises(ConfigurationError):
        HTTPProvider(config("openai")).request("chat", FAKE_KEY, "../?unsafe", "hello")
    with pytest.raises(APIError):
        HTTPProvider(
            config("openai"), Transport({"data": [{"embedding": [float("nan")]}]})
        ).request("embeddings", FAKE_KEY, "x", "hi")


def test_http_boundary():
    with patch("cae.providers.http.client.HTTPSConnection") as cls:
        response = cls.return_value.getresponse.return_value
        response.status, response.read.return_value = 200, b"{}"
        response.length = 0  # Real HTTPResponse decrements declared bytes as they are read.
        assert HTTPProviderTransport().send(config("openai"), "GET", "/v1/models", {}, None) == (
            200,
            b"{}",
        )
        assert cls.call_args.args[0] == "api.openai.com"
        assert cls.call_args.kwargs["context"].check_hostname
        cls.return_value.close.assert_called_once()
    with patch("cae.providers.http.client.HTTPConnection") as cls:
        cls.return_value.request.side_effect = RuntimeError(FAKE_KEY)
        with pytest.raises(APIError) as error:
            HTTPProviderTransport().send(config("ollama"), "GET", "/api/tags", {}, None)
        assert error.value.__context__ is None
    with pytest.raises(ConfigurationError):
        HTTPProviderTransport(0)
    with pytest.raises(ConfigurationError):
        HTTPProviderTransport().send(config("openai"), "GET", "//evil", {}, None)


def test_policy_atomic_daily_and_restart(tmp_path):
    day = ["2026-10-11"]
    rule = Rule("quota", "app", "openai", "default", frozenset({"models"}), max_requests_per_day=3)
    ledger = QuotaLedger(tmp_path / "quota.db", day=lambda: day[0])

    def reserve(_):
        try:
            ledger.reserve((rule,))
            return 1
        except QuotaExceeded:
            return 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        assert sum(pool.map(reserve, range(20))) == 3
    ledger.close()
    ledger = QuotaLedger(tmp_path / "quota.db", day=lambda: day[0])
    with pytest.raises(QuotaExceeded):
        ledger.reserve((rule,))
    day[0] = "2026-10-12"
    ledger.reserve((rule,))
    ledger.close()


def test_deny_overrides_and_model_allowlist():
    allow = Rule(
        "allow", "arx", "openai", "default", frozenset({"chat"}), models=frozenset({"gpt-5"})
    )
    deny = Rule(
        "deny", "arx", "openai", "default", frozenset({"chat"}), "deny", frozenset({"gpt-5"})
    )
    for policy, model in (
        (PolicyEngine((allow, deny)), "gpt-5"),
        (PolicyEngine((allow,)), "other-model"),
    ):
        with pytest.raises(AccessDenied):
            policy.authorize("arx", "openai", "default", "chat", model)
        policy.ledger.close()
    with pytest.raises(ConfigurationError):
        Rule("bad", "app", "openai", "default", frozenset({"export"}))
    with pytest.raises(ConfigurationError):
        Rule("bad", "app", "openai", "default", frozenset({"chat"}))


def test_sdk_policy_before_store_and_network(store):
    engine, access, transport = runtime(store)
    stranger = CAE(app="other", runtime=access)
    assert stranger.providers() == []
    with pytest.raises(AccessDenied):
        stranger.models()
    with pytest.raises(AccessDenied):
        engine.provider("openai").chat("unapproved", "hello")
    assert store.reads == 0 and transport.calls == []
    assert engine.health()["api"] == "unknown"
    assert engine.connect()["authentication"] == "valid"
    assert engine.get_status()["schema_version"] == 2
    assert engine.provider("openai").usage()["requests"] == 1
    assert engine.diagnostics()["policy_rules"] == 1
    assert snapshot(engine, "arx").provider_status == "available"
    assert FAKE_KEY not in json.dumps(engine.audit())
    assert any(event["event"] == "policy_denied" for event in engine.audit())
    assert all(event["app"] == "app" for event in engine.audit())
    engine.close()


def test_runtime_usage_errors_and_unsupported(store):
    engine, access, transport = runtime(
        store, data={"output": [], "usage": {"input_tokens": 5, "output_tokens": 2}}
    )
    assert engine.create_response("test-model", "hello")["usage"]["input_tokens"] == 5
    assert engine.provider("openai").usage()["input_tokens"] == 5
    transport.data, transport.status = {}, 401
    assert engine.connect()["authentication"] == "invalid"
    engine.close()
    engine, access, transport = runtime(store, kind="anthropic")
    with pytest.raises(UnsupportedOperation):
        engine.provider("anthropic").embeddings("test-model", "hello")
    assert not transport.calls
    engine.close()


def test_missing_secret_and_local_no_secret(store):
    engine, access, transport = runtime(store)
    store.delete("default")
    assert engine.connect()["credential"] == "missing"
    assert not transport.calls
    engine.close()
    engine, access, transport = runtime(store, kind="ollama", data={"models": []})
    store.reads = 0
    assert engine.connect()["authentication"] == "not_required"
    assert store.reads == 0
    assert engine.models() == []
    engine.close()


def test_persistent_metadata_audit_and_fail_closed(tmp_path, store):
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(path)
    engine, _, transport = runtime(store, audit=audit)
    engine.models()
    assert len(AuditLog(path).events(app="app")) == 3
    assert FAKE_KEY not in path.read_text()
    engine.close()
    engine, _, transport = runtime(store, audit=AuditLog(tmp_path))
    with pytest.raises(AuditError):
        engine.models()
    assert transport.calls == []
    engine.close()
    path.write_text('{"secret":"synthetic-invalid"}')
    with pytest.raises(AuditError):
        AuditLog(path).events()


def test_config_strict_and_persistent(tmp_path):
    text = Path("examples/access.toml").read_text()
    specs, rules = parse_config(text)
    assert len(specs) == 2 and len(rules) == 4
    for bad in (
        "oops",
        text + '\napi_key="never-accept"',
        text.replace('kind = "openai"', 'kind = "other"'),
        text + "\n# " + FAKE_KEY,
    ):
        with pytest.raises(ConfigurationError) as error:
            parse_config(bad)
        assert error.value.__context__ is None
    path = tmp_path / "cae.toml"
    path.write_text(text)
    access = load_runtime(path)
    assert access.providers("cae-console", "default")
    access.close()
    assert (tmp_path / ".cae/quotas.sqlite3").exists()
    with pytest.raises(ConfigurationError):
        load_runtime(tmp_path / "missing")


def test_custom_adapter_and_namespace(store):
    from cae.credential import CredentialManager, WindowsCredentialStore

    audit = AuditLog()
    manager = CredentialManager(store, provider="gemini", audit=audit)
    manager.add("a" * 39)
    manager.replace("b" * 39)
    manager.remove()
    assert {event["event"] for event in audit.events()} >= {
        "credential_added",
        "credential_replaced",
        "credential_removed",
    }
    with patch("cae.credential.os.name", "nt"), patch("cae.credential.ctypes.WinDLL"):
        assert WindowsCredentialStore("gemini")._target("default") == "CAE/gemini/default"
        assert WindowsCredentialStore()._target("default") == "CAE/openai/default"
    with pytest.raises(ConfigurationError):
        HTTPProvider(ProviderConfig("custom", "custom"))


def test_quota_shared_connections_and_error_sanitation(tmp_path):
    path = tmp_path / "shared.db"
    first, second = QuotaLedger(path), QuotaLedger(path)
    rule = Rule("shared", "app", "openai", "default", frozenset({"models"}), max_requests_per_day=1)
    first.reserve((rule,))
    with pytest.raises(QuotaExceeded):
        second.reserve((rule,))
    first.close()
    second.close()
    with pytest.raises(AccessDenied):
        first.reserve((rule,))
    with pytest.raises(ConfigurationError) as error:
        ProviderConfig("local", "vllm", "http://127.0.0.1:" + FAKE_KEY, authenticated=False)
    assert error.value.__context__ is None


def test_custom_provider_extension_has_no_sdk_secret_parameter():
    class Custom:
        config = ProviderConfig("custom", "custom", authenticated=False)
        capabilities = frozenset({"models"})

        def request(self, operation, secret, model, text, max_tokens):
            assert secret == "" and operation == "models"
            return {"models": ["custom-model"]}

    policy = PolicyEngine((Rule("custom-app", "app", "custom", "default", frozenset({"models"})),))
    engine = CAE(app="app", provider="custom", runtime=AccessRuntime((Custom(),), policy))
    assert engine.models() == ["custom-model"]
    engine.close()


def test_credential_backend_failure_has_no_secret_context(store):
    from cae.credential import CredentialManager

    def fail(*args):
        raise RuntimeError(FAKE_KEY)

    store.write = fail
    log = AuditLog()
    with pytest.raises(Exception) as error:
        CredentialManager(store, audit=log).add(FAKE_KEY)
    assert error.value.__context__ is None
    assert log.events()[-1]["event"] == "credential_failed"
    assert not any(e["event"] == "credential_added" for e in log.events())
