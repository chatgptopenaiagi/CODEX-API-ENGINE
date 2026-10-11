import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from cae import BrokerClient
from cae.access import AccessRuntime
from cae.audit import AuditLog
from cae.broker_client import BrokerRemoteError
from cae.broker_service import BrokerServer, main
from cae.errors import AccessDenied, ConfigurationError
from cae.ipc_protocol import BrokerSettings, Enrollment, decode, encode, request
from cae.pipe_transport import IPCError, Pipe, ProtocolError, pipe_path, process_peer
from cae.policy import PolicyEngine, Rule
from cae.providers import ProviderConfig

SECRET = "sk-" + "SyntheticOnlyForPipeSecurityTest" * 2


class Store:
    reads = 0

    def read(self, profile):
        self.reads += 1
        return SECRET

    def exists(self, profile):
        return True


class Adapter:
    config = ProviderConfig("openai", "openai")
    capabilities = frozenset({"models", "chat", "embeddings"})

    def request(self, operation, secret, model, text, max_tokens):
        assert secret == SECRET
        if operation == "models":
            return {"models": ["safe-model", secret]}
        return {"text": secret, "vectors": [[1.0]], "usage": {"input_tokens": 1}}


@pytest.fixture
def broker(tmp_path):
    peer = process_peer(os.getpid())
    enrollment = Enrollment("client-a", peer.image, peer.sha256)
    settings = BrokerSettings("cae-test-" + uuid4().hex, tmp_path / "runtime.toml",
                              enrollment, (enrollment,))
    store = Store()
    runtime = AccessRuntime((Adapter(),), PolicyEngine((Rule(
        "test", "client-a", "openai", "default",
        frozenset({"models", "health", "diagnostics", "chat", "embeddings", "usage"}),
        models=frozenset({"safe-model"}), max_requests_per_day=100,
    ),)), audit=AuditLog(), stores=lambda _: store)
    server = BrokerServer(settings, runtime)
    thread = threading.Thread(target=server.serve)
    thread.start()
    assert server.ready.wait(5)
    client = BrokerClient(settings.pipe, peer.image, peer.sha256)
    try:
        yield server, client, store
    finally:
        server.stopping.set()
        thread.join(8)
        assert not thread.is_alive()


def raw(server, payload):
    pipe = Pipe.dial(server.settings.pipe)
    try:
        pipe.send(payload)
        result = decode(pipe.receive())
        pipe.send(b"OK")
        return result
    finally:
        pipe.close()


def test_real_pipe_routing_and_non_disclosure(broker):
    server, client, store = broker
    assert client.get_status()["broker_pid"] == os.getpid()
    assert client.get_status()["app"] == "client-a"
    assert client.diagnostics()["credential"] == "stored"
    assert client.health(probe=True)["authentication"] == "valid"
    assert SECRET not in json.dumps(client.list_models())
    assert SECRET not in json.dumps(client.chat("safe-model", "hello"))
    assert client.embeddings("safe-model", "hello")["vectors"] == [[1.0]]
    assert client.request("usage")["requests"] == 4
    assert client.request("providers")["providers"]
    assert client.request("policies")["rules"]
    assert SECRET not in json.dumps(client.request("audit"))
    assert store.reads == 4


@pytest.mark.parametrize("operation,args", [
    ("stop", {}), ("export", {}), ("replace", {}), ("provider.modify", {}),
    ("models", {"app": "admin"}), ("models", {"profile": "other"}),
    ("models", {"provider": "other"}), ("chat", {"model": "forbidden", "text": "x"}),
    ("health", {"probe": "true"}), ("status", {"token": "fake"}),
    ("models", {"profile": 12}), ("chat", {"model": [], "text": "x"}),
    ("chat", {"model": "safe-model", "text": "x", "max_tokens": 0}),
])
def test_denied_before_credential_access(broker, operation, args):
    _, client, store = broker
    with pytest.raises(BrokerRemoteError):
        client.request(operation, **args)
    assert store.reads == 0
    assert client.get_status()["broker"] == "ready"


@pytest.mark.parametrize("payload", [
    b"{}", b"[]", b"null", b"{", b'{"a":1,"a":2}', b'{"a":NaN}', b"\xff",
    encode({"v": 2, "id": "0" * 32, "op": "status", "args": {}}),
    encode({"v": 1, "id": "0" * 32, "op": "status", "args": {}, "app": "admin"}),
])
def test_malformed_requests(broker, payload):
    server, client, _ = broker
    assert raw(server, payload)["error"] == "invalid_protocol"
    assert client.get_status()["broker"] == "ready"


def test_identity_authentication(broker):
    server, client, store = broker
    enrollment = server.settings.clients[0]
    peer = process_peer(os.getpid())
    for changed in [replace(peer, sid="S-1-5-7"), replace(peer, sha256="0" * 64),
                    replace(peer, image=str(Path(peer.image).parent / "other.exe"))]:
        with pytest.raises(AccessDenied):
            server.settings.authenticate(changed, peer.sid)
    server.settings = replace(server.settings, clients=(replace(enrollment, sha256="0" * 64),))
    with pytest.raises(BrokerRemoteError, match="access_denied"):
        client.list_models()
    assert store.reads == 0


def test_server_pinning(broker):
    server, client, _ = broker
    bad = BrokerClient(server.settings.pipe, client.server.image, "0" * 64)
    with pytest.raises(IPCError):
        bad.get_status()


def test_oversized_and_partial_frames_timeout(broker):
    server, client, _ = broker
    pipe = Pipe.dial(server.settings.pipe)
    try:
        import ctypes
        value = ctypes.create_string_buffer((65_537).to_bytes(4, "little"))
        pipe._io("write", value, 4, time.monotonic() + 1)
        assert decode(pipe.receive())["error"] == "invalid_protocol"
        pipe.send(b"OK")
    finally:
        pipe.close()
    pipe = Pipe.dial(server.settings.pipe)
    try:
        value = ctypes.create_string_buffer(b"\x10")
        pipe._io("write", value, 1, time.monotonic() + 1)
        started = time.monotonic()
        assert decode(pipe.receive(4))["error"] == "broker_unavailable"
        assert time.monotonic() - started < 3.5
        pipe.send(b"OK")
    finally:
        pipe.close()
    assert client.get_status()["broker"] == "ready"


def test_concurrency_and_repeated_connections(broker):
    _, client, _ = broker
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: client.get_status(), range(40)))
    assert all(row["broker_pid"] == os.getpid() for row in results)


def test_exhaustion_recovers(broker):
    server, client, _ = broker
    pipes = [Pipe.dial(server.settings.pipe) for _ in range(8)]
    try:
        with pytest.raises(IPCError):
            Pipe.dial(server.settings.pipe, timeout=0.1)
    finally:
        for pipe in pipes:
            pipe.close()
    assert client.get_status()["broker"] == "ready"


def test_admin_stop_and_first_instance(broker):
    server, client, _ = broker
    with pytest.raises(IPCError):
        Pipe.listener(server.settings.pipe, server.identity.sid, first=True)
    enrollment = replace(server.settings.clients[0], admin=True)
    server.settings = replace(server.settings, clients=(enrollment,))
    assert client.stop()["broker"] == "stopping"
    assert server.stopping.is_set()


def test_config_validation(tmp_path):
    peer = process_peer(os.getpid())
    identity = {"app": "client", "image": peer.image, "sha256": peer.sha256}
    path = tmp_path / "broker.json"
    data = {"version": 1, "pipe": "cae-tests", "runtime": str(tmp_path / "runtime.toml"),
            "server": identity, "clients": [identity]}
    path.write_text(json.dumps(data))
    assert BrokerSettings.load(path).pipe == "cae-tests"
    for key, value in [("version", True), ("pipe", "\\\\remote\\pipe\\x"),
                       ("runtime", "relative"), ("clients", [identity, identity]),
                       ("clients", []), ("unknown", "ignored")]:
        path.write_text(json.dumps({**data, key: value}))
        with pytest.raises(ConfigurationError):
            BrokerSettings.load(path)
    for image, hash_value, admin in [("relative", peer.sha256, False),
                                     (peer.image, "bad", False), (peer.image, peer.sha256, 1)]:
        with pytest.raises(ConfigurationError):
            Enrollment("app", image, hash_value, admin)


def test_protocol_limits_and_smoke():
    with pytest.raises(ProtocolError):
        pipe_path("remote")
    with pytest.raises(ProtocolError):
        encode({"huge": "a" * 65536})
    with pytest.raises(ProtocolError):
        request(b"{}")
    assert main(["--self-test"]) == 0
    assert main([]) == 1
