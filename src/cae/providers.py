"""Trusted provider adapters. Applications receive broker-bound sessions, never adapters."""

import http.client
import json
import math
import re
import socket
import ssl
from dataclasses import asdict, dataclass
from threading import Timer
from typing import Any, Protocol
from urllib.parse import quote, urlsplit

from .errors import APIError, ConfigurationError, UnsupportedOperation
from .policy import MODEL
from .security import identifier, redact
from .version import __version__

CLOUD = {
    "openai": "https://api.openai.com",
    "anthropic": "https://api.anthropic.com",
    "gemini": "https://generativelanguage.googleapis.com",
}
LOCAL = {
    "ollama": "http://127.0.0.1:11434",
    "vllm": "http://127.0.0.1:8000",
    "lmstudio": "http://127.0.0.1:1234",
}


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    name: str
    kind: str
    endpoint: str = ""
    profile: str = "default"
    authenticated: bool = True

    def __post_init__(self) -> None:
        identifier(self.name)
        identifier(self.profile)
        endpoint = self.endpoint or CLOUD.get(self.kind, LOCAL.get(self.kind, ""))
        object.__setattr__(self, "endpoint", endpoint)
        invalid = False
        url = urlsplit("")
        try:
            url = urlsplit(endpoint)
            _ = url.port
        except Exception:
            invalid = True
        if invalid:
            raise ConfigurationError()
        if url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
            raise ConfigurationError()
        if self.kind in CLOUD:
            if endpoint != CLOUD[self.kind] or not self.authenticated:
                raise ConfigurationError()
        elif self.kind == "azure-openai":
            if (
                not re.fullmatch(r"https://[a-z0-9][a-z0-9-]{0,62}\.openai\.azure\.com", endpoint)
                or not self.authenticated
            ):
                raise ConfigurationError()
        elif self.kind in LOCAL:
            if url.scheme not in {"http", "https"} or url.hostname not in {"127.0.0.1", "::1"}:
                raise ConfigurationError()
            if url.port is None or not 1 <= url.port <= 65535:
                raise ConfigurationError()
            if self.kind == "ollama" and self.authenticated:
                raise ConfigurationError()
        elif self.kind == "custom":
            if endpoint:
                raise ConfigurationError()
        else:
            raise ConfigurationError()


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    reported: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ChatResult:
    text: str
    usage: Usage

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProviderTransport(Protocol):
    def send(
        self,
        config: ProviderConfig,
        method: str,
        path: str,
        headers: dict[str, str],
        payload: dict[str, Any] | None,
    ) -> tuple[int, bytes]: ...


class HTTPProviderTransport:
    def __init__(self, timeout: float = 15, *, body_timeout: float = 20) -> None:
        if not 0 < timeout <= 120 or not 0 < body_timeout <= 120:
            raise ConfigurationError()
        self.timeout = timeout
        self.body_timeout = body_timeout

    def send(
        self,
        config: ProviderConfig,
        method: str,
        path: str,
        headers: dict[str, str],
        payload: dict[str, Any] | None,
    ) -> tuple[int, bytes]:
        url = urlsplit(config.endpoint)
        if not path.startswith("/") or path.startswith("//") or "\r" in path or "\n" in path:
            raise ConfigurationError()
        connection: http.client.HTTPConnection
        if url.scheme == "https":
            connection = http.client.HTTPSConnection(
                url.hostname or "",
                url.port,
                timeout=self.timeout,
                context=ssl.create_default_context(),
            )
        else:
            connection = http.client.HTTPConnection(
                url.hostname or "", url.port, timeout=self.timeout
            )
        connection.set_debuglevel(0)
        failed = False
        result = (0, b"")
        timer: Timer | None = None
        try:
            connection.connect()
            connected_socket = connection.sock

            def interrupt() -> None:
                if connected_socket is not None:
                    try:
                        connected_socket.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass

            # Bound a slow/trickling peer after connection, including response headers/body.
            timer = Timer(self.body_timeout, interrupt)
            timer.daemon = True
            timer.start()
            connection.request(
                method,
                path,
                body=json.dumps(payload).encode() if payload is not None else None,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "CAE/" + __version__,
                    **headers,
                },
            )
            response = connection.getresponse()
            data = response.read(4 * 1024 * 1024 + 1)
            if len(data) > 4 * 1024 * 1024:
                raise ValueError()
            result = response.status, data
        except Exception:
            failed = True
        finally:
            if timer is not None:
                timer.cancel()
                timer.join()
            connection.close()
        if failed:
            raise APIError("unavailable")
        return result


class ProviderAdapter(Protocol):
    config: ProviderConfig
    capabilities: frozenset[str]

    def request(
        self, operation: str, secret: str, model: str | None, text: str | None, max_tokens: int
    ) -> dict[str, Any]: ...


class HTTPProvider:
    def __init__(self, config: ProviderConfig, transport: ProviderTransport | None = None) -> None:
        if config.kind == "custom":
            raise ConfigurationError()
        self.config = config
        self._transport = transport if transport is not None else HTTPProviderTransport()
        self.capabilities = frozenset(
            {"models", "chat"} | ({"embeddings"} if config.kind != "anthropic" else set())
        )

    def request(
        self,
        operation: str,
        secret: str,
        model: str | None = None,
        text: str | None = None,
        max_tokens: int = 256,
    ) -> dict[str, Any]:
        if operation not in self.capabilities:
            raise UnsupportedOperation()
        if operation != "models" and (
            model is None
            or not MODEL.fullmatch(model)
            or not isinstance(text, str)
            or not 1 <= len(text) <= 100_000
        ):
            raise ConfigurationError()
        if type(max_tokens) is not int or not 1 <= max_tokens <= 32768:
            raise ConfigurationError()
        method, path, headers, payload = self._wire(
            operation, secret, model or "", text or "", max_tokens
        )
        failed = False
        status, body = 0, b""
        try:
            status, body = self._transport.send(self.config, method, path, headers, payload)
        except Exception:
            failed = True
        if failed:
            raise APIError("unavailable")
        if not 200 <= status < 300:
            raise APIError(
                {401: "authentication", 403: "permission", 429: "rate_limit"}.get(
                    status, "unavailable" if status >= 500 else "request"
                ),
                status,
            )
        invalid = False
        result: dict[str, Any] = {}
        try:
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ValueError()
            result = self._normalize(operation, value)
        except Exception:
            invalid = True
        if invalid:
            raise APIError("protocol", status)
        safe: dict[str, Any] = redact(result, secret)
        return safe

    def _wire(
        self, op: str, secret: str, model: str, text: str, limit: int
    ) -> tuple[str, str, dict[str, str], dict[str, Any] | None]:
        kind = self.config.kind
        headers: dict[str, str] = {}
        if self.config.authenticated:
            header = {
                "anthropic": "x-api-key",
                "gemini": "x-goog-api-key",
                "azure-openai": "api-key",
            }.get(kind, "Authorization")
            headers[header] = "Bearer " + secret if header == "Authorization" else secret
        if kind == "anthropic":
            headers["anthropic-version"] = "2023-06-01"
            return (
                ("GET", "/v1/models", headers, None)
                if op == "models"
                else (
                    "POST",
                    "/v1/messages",
                    headers,
                    {
                        "model": model,
                        "messages": [{"role": "user", "content": text}],
                        "max_tokens": limit,
                    },
                )
            )
        if kind == "gemini":
            if op == "models":
                return "GET", "/v1beta/models", headers, None
            model = model.removeprefix("models/")
            path = "/v1beta/models/" + quote(model, safe="")
            if op == "chat":
                return (
                    "POST",
                    path + ":generateContent",
                    headers,
                    {
                        "contents": [{"role": "user", "parts": [{"text": text}]}],
                        "generationConfig": {"maxOutputTokens": limit},
                    },
                )
            return (
                "POST",
                path + ":embedContent",
                headers,
                {"model": "models/" + model, "content": {"parts": [{"text": text}]}},
            )
        if kind == "ollama":
            if op == "models":
                return "GET", "/api/tags", {}, None
            if op == "chat":
                return (
                    "POST",
                    "/api/chat",
                    {},
                    {
                        "model": model,
                        "messages": [{"role": "user", "content": text}],
                        "stream": False,
                        "options": {"num_predict": limit},
                    },
                )
            return "POST", "/api/embed", {}, {"model": model, "input": text}
        prefix = "/openai/v1" if kind == "azure-openai" else "/v1"
        if op == "models":
            return "GET", prefix + "/models", headers, None
        if op == "embeddings":
            return "POST", prefix + "/embeddings", headers, {"model": model, "input": text}
        if kind == "openai":
            return (
                "POST",
                "/v1/responses",
                headers,
                {"model": model, "input": text, "max_output_tokens": limit, "store": False},
            )
        token_field = "max_completion_tokens" if kind == "azure-openai" else "max_tokens"
        return (
            "POST",
            prefix + "/chat/completions",
            headers,
            {
                "model": model,
                "messages": [{"role": "user", "content": text}],
                token_field: limit,
                "stream": False,
            },
        )

    def _normalize(self, op: str, data: dict[str, Any]) -> dict[str, Any]:
        kind = self.config.kind
        if op == "models":
            rows = data["models"] if kind in {"gemini", "ollama"} else data["data"]
            key = "name" if kind in {"gemini", "ollama"} else "id"
            if not isinstance(rows, list) or any(not isinstance(row.get(key), str) for row in rows):
                raise ValueError()
            return {
                "models": [
                    row[key].removeprefix("models/") if kind == "gemini" else row[key]
                    for row in rows
                ],
                "truncated": bool(data.get("has_more") or data.get("nextPageToken")),
            }
        usage = data.get("usage", {})
        incoming = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        outgoing = usage.get("output_tokens", usage.get("completion_tokens", 0))
        reported = bool(usage)
        if kind == "gemini":
            usage = data.get("usageMetadata", {})
            incoming, outgoing = (
                usage.get("promptTokenCount", 0),
                usage.get("candidatesTokenCount", 0),
            )
            reported = bool(usage)
        elif kind == "ollama":
            incoming, outgoing = data.get("prompt_eval_count", 0), data.get("eval_count", 0)
            reported = "prompt_eval_count" in data
        if type(incoming) is not int or type(outgoing) is not int or min(incoming, outgoing) < 0:
            raise ValueError()
        tokens = Usage(incoming, outgoing, reported)
        if op == "embeddings":
            vectors = (
                [data["embedding"]["values"]]
                if kind == "gemini"
                else data["embeddings"]
                if kind == "ollama"
                else [row["embedding"] for row in data["data"]]
            )
            if (
                not isinstance(vectors, list)
                or not vectors
                or any(
                    not isinstance(v, list)
                    or not v
                    or any(type(x) not in {int, float} or not math.isfinite(x) for x in v)
                    for v in vectors
                )
            ):
                raise ValueError()
            return {"vectors": vectors, "usage": tokens.to_dict()}
        if kind == "openai":
            content = [
                part["text"]
                for item in data["output"]
                if item.get("type") == "message"
                for part in item["content"]
                if part.get("type") == "output_text"
            ]
        elif kind == "anthropic":
            content = [part["text"] for part in data["content"] if part.get("type") == "text"]
        elif kind == "gemini":
            content = [
                part["text"] for part in data["candidates"][0]["content"]["parts"] if "text" in part
            ]
        elif kind == "ollama":
            content = [data["message"]["content"]]
        else:
            content = [data["choices"][0]["message"]["content"]]
        if any(not isinstance(part, str) for part in content):
            raise ValueError()
        return ChatResult("".join(content), tokens).to_dict()
