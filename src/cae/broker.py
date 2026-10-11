"""In-process policy broker for trusted hosts. Not an OS process isolation boundary."""

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from .api import OpenAIConnector
from .credential import CredentialStore
from .errors import AccessDenied, CAEError, CredentialError
from .security import identifier


@dataclass(frozen=True, slots=True)
class Grant:
    app: str
    profile: str
    operations: frozenset[str]

    def __post_init__(self) -> None:
        identifier(self.app)
        identifier(self.profile)
        object.__setattr__(self, "operations", frozenset(self.operations))
        if not self.operations or not self.operations <= {"models", "responses"}:
            raise AccessDenied()


class Broker:
    def __init__(
        self,
        store: CredentialStore,
        grants: tuple[Grant, ...],
        connector: OpenAIConnector | None = None,
    ) -> None:
        self._store = store
        self._grants = tuple(grants)
        self._connector = connector if connector is not None else OpenAIConnector()
        self._events: deque[dict[str, str]] = deque(maxlen=100)
        self._lock = RLock()

    def _allowed(self, app: str, profile: str, operation: str) -> bool:
        return any(
            g.app == app and g.profile == profile and operation in g.operations
            for g in self._grants
        )

    def _audit(self, outcome: str) -> None:
        with self._lock:
            self._events.append({"time": datetime.now(UTC).isoformat(), "outcome": outcome})

    def audit(self) -> list[dict[str, str]]:
        with self._lock:
            return [dict(event) for event in self._events]

    def configured(self, app: str, profile: str) -> bool:
        if not any(self._allowed(app, profile, op) for op in ("models", "responses")):
            raise AccessDenied()
        return self._store.exists(profile)

    def execute(
        self,
        app: str,
        profile: str,
        operation: str,
        payload: dict[str, Any] | None = None,
        *,
        single_attempt: bool = False,
    ) -> dict[str, Any]:
        if not self._allowed(app, profile, operation):
            self._audit("denied")
            raise AccessDenied()
        secret = ""
        storage_failed = False
        try:
            secret = self._store.read(profile)
        except Exception:
            storage_failed = True
        if storage_failed:
            self._audit("credential_failed")
            raise CredentialError()
        try:
            result = self._connector.request(
                secret, operation, payload, single_attempt=single_attempt
            )
        except CAEError:
            self._audit("request_failed")
            raise
        else:
            self._audit("success")
            return result
        finally:
            secret = ""
