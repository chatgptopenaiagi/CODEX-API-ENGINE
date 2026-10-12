import json
import os
from types import SimpleNamespace

import pytest

from cae import BrokerClient
from cae.credential import WindowsCredentialStore
from cae.errors import CredentialError
from cae.pipe_transport import IPCError, ProtocolError, WinAPI, process_peer


@pytest.mark.parametrize("failure", ["process", "image", "token", "token_info", "token_info_read", "sid_string"])
def test_peer_lookup_fails_closed_and_releases_handles(monkeypatch, failure):
    api = WinAPI()
    closed = []
    close = api.close

    def record(handle):
        closed.append(handle)
        return close(handle)

    api.close = record
    if failure == "token_info_read":
        token_info = api.token_info
        calls = []

        def fail_second(*args):
            calls.append(True)
            return token_info(*args) if len(calls) == 1 else 0

        api.token_info = fail_second
    else:
        setattr(api, failure, lambda *args: 0)
    monkeypatch.setattr("cae.pipe_transport.WinAPI", lambda: api)
    with pytest.raises(IPCError):
        process_peer(os.getpid())
    assert len(closed) == (0 if failure == "process" else 1 if failure in {"image", "token"} else 2)


def test_unsupported_platform_has_no_plaintext_fallback(monkeypatch):
    monkeypatch.setattr("cae.pipe_transport.os", SimpleNamespace(name="posix"))
    monkeypatch.setattr("cae.credential.os", SimpleNamespace(name="posix"))
    with pytest.raises(IPCError):
        WinAPI()
    with pytest.raises(CredentialError):
        WindowsCredentialStore()


@pytest.mark.parametrize("patch", [
    {"v": True}, {"v": 1.0}, {"broker_pid": True}, {"ok": True, "error": "unexpected"},
    {"ok": False, "error": {}}, {"result": []},
])
def test_response_types_are_strict(monkeypatch, patch):
    peer = process_peer(os.getpid())

    class FakePipe:
        identity = ""
        closed = False

        def send(self, data):
            if data != b"OK":
                self.identity = json.loads(data)["id"]

        def receive(self, timeout):
            return json.dumps({"v": 1, "id": self.identity, "ok": True, "error": None,
                               "result": {}, "broker_pid": peer.pid, **patch}).encode()

        def peer(self, server):
            return peer

        def close(self):
            self.closed = True

    pipe = FakePipe()
    monkeypatch.setattr("cae.broker_client.Pipe.dial", lambda *args: pipe)
    client = BrokerClient("cae-test", peer.image, peer.sha256)
    with pytest.raises(ProtocolError):
        client.get_status()
    assert pipe.closed
