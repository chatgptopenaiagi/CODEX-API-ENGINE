"""Schema-constrained metadata audit; no prompts, results, headers or exception strings."""

import json
import math
import time
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Any, ParamSpec, TypeVar
from uuid import uuid4

from .errors import AuditError, ConfigurationError
from .security import identifier, redact

_REQUEST: ContextVar[tuple[str, float] | None] = ContextVar("cae_audit_request", default=None)
_P = ParamSpec("_P")
_T = TypeVar("_T")
ERROR_CODES = frozenset({"none", "engine_error", "invalid_configuration",
    "credential_operation_failed", "credential_missing", "credential_already_exists",
    "access_denied", "unsupported_operation", "daily_request_limit", "request_rate_limit",
    "concurrent_request_limit", "audit_unavailable", "api_request_failed",
    "invalid_protocol", "broker_unavailable", "ipc_timeout"})


@contextmanager
def request_scope() -> Iterator[str]:
    """Broker-generated identity; nested runtime calls share it, threads do not."""
    existing = _REQUEST.get()
    token = None
    if existing is None:
        existing = (uuid4().hex, time.monotonic())
        token = _REQUEST.set(existing)
    try:
        yield existing[0]
    finally:
        if token is not None:
            _REQUEST.reset(token)


def correlated(function: Callable[_P, _T]) -> Callable[_P, _T]:
    @wraps(function)
    def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        with request_scope():
            return function(*args, **kwargs)
    return wrapped

EVENTS = frozenset(
    {
        "credential_change_requested",
        "credential_added",
        "credential_replaced",
        "credential_removed",
        "credential_checked",
        "credential_failed",
        "policy_granted",
        "policy_denied",
        "request_completed",
        "request_failed",
        "authentication_failed",
        "provider_connected",
        "provider_disconnected",
        "diagnostics_read",
        "health_read",
        "providers_read",
        "policies_read",
        "audit_read",
        "usage_read",
        "configuration_loaded",
        "broker_started",
        "broker_stopping",
        "broker_status",
        "ipc_authenticated",
        "ipc_denied",
        "application_registered",
        "application_change_requested",
        "application_authorized",
        "application_revoked",
        "ipc_result",
    }
)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    timestamp: str
    event: str
    app: str
    provider: str
    profile: str
    operation: str
    request_id: str = ""
    decision: str = "none"
    status: str = "none"
    error_code: str = "none"
    latency_ms: float | None = None

    def validate(self) -> None:
        if self.event not in EVENTS:
            raise ValueError()
        for value in (self.app, self.provider, self.profile, self.operation):
            identifier(value)
        if not isinstance(self.request_id, str):
            raise ValueError()
        for value in (self.event_id, self.request_id or self.event_id):
            if not isinstance(value, str) or len(value) != 32 or any(
                c not in "0123456789abcdef" for c in value
            ):
                raise ValueError()
        datetime.fromisoformat(self.timestamp)
        if (self.decision not in {"none", "allow", "deny"}
                or self.status not in {"none", "ok", "error"}
                or self.error_code not in ERROR_CODES
                or (self.latency_ms is not None and (
                    type(self.latency_ms) not in {int, float}
                    or not math.isfinite(self.latency_ms) or self.latency_ms < 0))):
            raise ValueError()

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = redact(asdict(self))
        return result


class AuditLog:
    """Optional append-only JSONL sink. Sink failure blocks subsequent execution."""

    def __init__(self, path: Path | None = None, capacity: int = 1000) -> None:
        if not 1 <= capacity <= 100_000:
            raise ConfigurationError()
        self._path = path
        self._events: deque[AuditEvent] = deque(maxlen=capacity)
        self._lock = RLock()

    def emit(
        self,
        event: str,
        *,
        app: str = "admin",
        provider: str = "none",
        profile: str = "default",
        operation: str = "none",
        error_code: str = "none",
    ) -> AuditEvent:
        if event not in EVENTS:
            raise ConfigurationError()
        for value in (app, provider, profile, operation):
            identifier(value)
        if error_code not in ERROR_CODES:
            error_code = "engine_error"
        context = _REQUEST.get()
        denied = event in {"policy_denied", "ipc_denied"}
        failed_event = denied or event.endswith("failed") or error_code != "none"
        entry = AuditEvent(
            uuid4().hex, datetime.now(UTC).isoformat(), event, app, provider, profile, operation,
            request_id=context[0] if context else "",
            decision="deny" if denied else "allow" if event == "policy_granted" else "none",
            status="error" if failed_event else "ok",
            error_code=error_code,
            latency_ms=round(max(0, time.monotonic() - context[1]) * 1000, 3)
            if context else None,
        )
        failed = False
        with self._lock:
            if self._path is not None:
                try:
                    if self._path.is_symlink():
                        raise OSError()
                    self._path.parent.mkdir(parents=True, exist_ok=True)
                    with self._path.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(entry.to_dict(), allow_nan=False) + "\n")
                        stream.flush()
                except Exception:
                    failed = True
            if not failed:
                self._events.append(entry)
        if failed:
            raise AuditError()
        return entry

    def events(self, *, app: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if self._path is None:
                return [
                    event.to_dict() for event in self._events if app is None or event.app == app
                ]
            failed = False
            rows: list[dict[str, Any]] = []
            try:
                with self._path.open("rb") as stream:
                    stream.seek(0, 2)
                    offset = max(0, stream.tell() - 1_000_000)
                    stream.seek(offset)
                    if offset:
                        stream.readline()
                    lines = stream.read().decode("utf-8").splitlines()
                for line in lines[-self._events.maxlen :] if self._events.maxlen else lines:
                    event = AuditEvent(**json.loads(line))
                    event.validate()
                    if app is None or event.app == app:
                        rows.append(event.to_dict())
            except Exception:
                failed = True
            if failed:
                raise AuditError()
            return rows
