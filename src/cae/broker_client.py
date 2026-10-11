"""Public IPC SDK: no credential store or broker implementation imports."""

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from .errors import CAEError
from .ipc_protocol import Enrollment, decode, encode
from .pipe_transport import IPCError, Pipe, ProtocolError, process_peer


class BrokerRemoteError(CAEError):
    def __init__(self, code: str) -> None:
        self.code = code if code in {
            "access_denied", "invalid_protocol", "invalid_configuration", "daily_request_limit",
            "credential_operation_failed", "credential_missing", "api_request_failed",
            "unsupported_operation", "audit_unavailable", "broker_unavailable",
            "request_rate_limit", "concurrent_request_limit",
        } else "broker_request_failed"
        super().__init__()


class BrokerClient:
    """Fresh OS-authenticated connection per call; never retries provider operations."""

    def __init__(self, pipe: str, server_image: str | Path, server_sha256: str,
                 *, timeout: float = 35) -> None:
        if not 0 < timeout <= 120:
            raise ProtocolError()
        self.pipe = pipe
        self.server = Enrollment("broker", str(server_image), server_sha256)
        self.timeout = timeout
        self._sid = process_peer(os.getpid()).sid

    def request(self, operation: str, **arguments: Any) -> dict[str, Any]:
        identity = uuid4().hex
        raw = encode({"v": 1, "id": identity, "op": operation, "args": arguments})
        pipe = Pipe.dial(self.pipe, min(self.timeout, 3))
        try:
            peer = pipe.peer(server=True)
            if peer.sid != self._sid or not self.server.matches(peer):
                raise IPCError()
            pipe.send(raw)
            value = decode(pipe.receive(self.timeout))
            pipe.send(b"OK")  # Drain handshake: server never uses blocking FlushFileBuffers.
            if (set(value) != {"v", "id", "ok", "result", "error", "broker_pid"}
                    or type(value["v"]) is not int or value["v"] != 1 or value["id"] != identity
                    or type(value["ok"]) is not bool or type(value["broker_pid"]) is not int
                    or value["broker_pid"] != peer.pid or not isinstance(value["result"], dict)
                    or (value["ok"] and value["error"] is not None)
                    or (not value["ok"] and not isinstance(value["error"], str))):
                raise ProtocolError()
            if not value["ok"]:
                raise BrokerRemoteError(value["error"])
            return dict(value["result"])
        finally:
            pipe.close()

    def get_status(self) -> dict[str, Any]:
        return self.request("status")

    def health(self, provider: str = "openai", profile: str = "default",
               *, probe: bool = False) -> dict[str, Any]:
        return self.request("health", provider=provider, profile=profile, probe=probe)

    def diagnostics(self, provider: str = "openai", profile: str = "default") -> dict[str, Any]:
        return self.request("diagnostics", provider=provider, profile=profile)

    def list_models(self, provider: str = "openai", profile: str = "default") -> dict[str, Any]:
        return self.request("models", provider=provider, profile=profile)

    def chat(self, model: str, text: str, *, provider: str = "openai",
             profile: str = "default", max_tokens: int = 256) -> dict[str, Any]:
        return self.request("chat", provider=provider, profile=profile,
                            model=model, text=text, max_tokens=max_tokens)

    def embeddings(self, model: str, text: str, *, provider: str = "openai",
                   profile: str = "default") -> dict[str, Any]:
        return self.request("embeddings", provider=provider, profile=profile,
                            model=model, text=text)

    def stop(self) -> dict[str, Any]:
        """Denied unless this executable is separately enrolled as administrator."""
        return self.request("stop")
