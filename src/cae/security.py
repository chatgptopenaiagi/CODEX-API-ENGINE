"""Small, auditable validation and output sanitation boundary."""

import re
from collections.abc import Mapping
from typing import Any

from .errors import ConfigurationError, CredentialError

_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
_SECRET = re.compile(r"sk-[A-Za-z0-9_-]+|Bearer\s+\S+", re.IGNORECASE)
_SENSITIVE = {
    "authorization",
    "api_key",
    "apikey",
    "key",
    "token",
    "secret",
    "credential",
    "password",
}


def identifier(value: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ConfigurationError()
    return value


def validate_key(value: str, provider: str = "openai") -> None:
    # Only a local syntax check; OpenAI is the authority on credential validity.
    pattern = (
        r"sk-[A-Za-z0-9_-]{16,2045}" if provider == "openai" else r"[A-Za-z0-9_./+=:-]{16,2048}"
    )
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise CredentialError()


def redact(value: Any, secret: str | None = None) -> Any:
    if isinstance(value, str):
        if secret:
            value = value.replace(secret, "[REDACTED]")
        return _SECRET.sub("[REDACTED]", value)
    if isinstance(value, Mapping):
        return {
            str(redact(str(k), secret)): (
                "[REDACTED]" if str(k).lower() in _SENSITIVE else redact(v, secret)
            )
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v, secret) for v in value]
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return "[REDACTED]"
