"""Schema-constrained metadata audit; no prompts, results, headers or exception strings."""

import json
from collections import deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from .errors import AuditError, ConfigurationError
from .security import identifier, redact

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
    ) -> AuditEvent:
        if event not in EVENTS:
            raise ConfigurationError()
        for value in (app, provider, profile, operation):
            identifier(value)
        entry = AuditEvent(
            uuid4().hex, datetime.now(UTC).isoformat(), event, app, provider, profile, operation
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
                    if event.event not in EVENTS:
                        raise ValueError()
                    for field in (event.app, event.provider, event.profile, event.operation):
                        identifier(field)
                    if len(event.event_id) != 32 or not all(
                        c in "0123456789abcdef" for c in event.event_id
                    ):
                        raise ValueError()
                    datetime.fromisoformat(event.timestamp)
                    if app is None or event.app == app:
                        rows.append(event.to_dict())
            except Exception:
                failed = True
            if failed:
                raise AuditError()
            return rows
