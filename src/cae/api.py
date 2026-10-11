"""Fixed-origin HTTPS connector. No redirects, proxies, raw error bodies or wire logs."""

import http.client
import json
import ssl
import time
from typing import Any, Protocol

from .errors import APIError, ConfigurationError
from .security import redact

MAX_BODY = 4 * 1024 * 1024


class Transport(Protocol):
    def send(
        self, method: str, path: str, secret: str, payload: dict[str, Any] | None
    ) -> tuple[int, bytes]: ...


class HTTPSTransport:
    def __init__(self, timeout: float = 15.0) -> None:
        if not 0 < timeout <= 120:
            raise ConfigurationError()
        self._timeout = timeout

    def send(
        self, method: str, path: str, secret: str, payload: dict[str, Any] | None
    ) -> tuple[int, bytes]:
        if (method, path) not in {("GET", "/v1/models"), ("POST", "/v1/responses")}:
            raise ConfigurationError()
        connection = http.client.HTTPSConnection(
            "api.openai.com", timeout=self._timeout, context=ssl.create_default_context()
        )
        connection.set_debuglevel(0)
        failed = False
        result = (0, b"")
        try:
            body = json.dumps(payload).encode("utf-8") if payload is not None else None
            connection.request(
                method,
                path,
                body=body,
                headers={
                    "Authorization": "Bearer " + secret,
                    "Content-Type": "application/json",
                    "User-Agent": "CAE/0.2.0",
                },
            )
            response = connection.getresponse()
            data = response.read(MAX_BODY + 1)
            if len(data) > MAX_BODY:
                raise ValueError()
            result = response.status, data
        except Exception:
            failed = True
        finally:
            connection.close()
        # Raised outside the handler so the original exception is not retained as context.
        if failed:
            raise APIError("unavailable")
        return result


class OpenAIConnector:
    def __init__(self, transport: Transport | None = None, retries: int = 2) -> None:
        if not isinstance(retries, int) or not 0 <= retries <= 3:
            raise ConfigurationError()
        self._transport = transport if transport is not None else HTTPSTransport()
        self._retries = retries

    def request(
        self,
        secret: str,
        operation: str,
        payload: dict[str, Any] | None = None,
        *,
        single_attempt: bool = False,
    ) -> dict[str, Any]:
        routes = {"models": ("GET", "/v1/models"), "responses": ("POST", "/v1/responses")}
        if operation not in routes:
            raise ConfigurationError()
        method, path = routes[operation]
        # Never retry generation automatically: an ambiguous failure may already be billed.
        attempts = 1 if single_attempt or method == "POST" else self._retries + 1
        for attempt in range(attempts):
            failed = False
            status, body = 0, b""
            try:
                status, body = self._transport.send(method, path, secret, payload)
            except Exception:
                failed = True
            if failed:
                if attempt + 1 < attempts:
                    time.sleep(0.25 * 2**attempt)
                    continue
                raise APIError("unavailable")
            if status in (429, 500, 502, 503, 504) and attempt + 1 < attempts:
                time.sleep(0.25 * 2**attempt)
                continue
            if not 200 <= status < 300:
                kind = {401: "authentication", 403: "permission", 429: "rate_limit"}.get(
                    status, "unavailable" if status >= 500 else "request"
                )
                raise APIError(kind, status)
            invalid = False
            value: Any = None
            try:
                value = json.loads(body)
                if not isinstance(value, dict):
                    invalid = True
            except Exception:
                invalid = True
            if invalid:
                raise APIError("protocol", status)
            cleaned: dict[str, Any] = redact(value, secret)
            return cleaned
        raise APIError()
