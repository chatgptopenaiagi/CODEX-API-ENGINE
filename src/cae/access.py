"""Capability broker: authorization precedes credential lookup and provider I/O."""

import time
from collections.abc import Callable
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from .audit import AuditLog, correlated
from .credential import CredentialStore, WindowsCredentialStore
from .errors import (
    AccessDenied,
    APIError,
    CAEError,
    ConcurrentLimitExceeded,
    ConfigurationError,
    CredentialError,
    UnsupportedOperation,
)
from .policy import MODEL, PolicyEngine, Rule
from .providers import HTTPProvider, ProviderAdapter, ProviderConfig
from .security import identifier, redact, validate_key


class AccessRuntime:
    """Trusted host composition root. Not exposed as a remote identity boundary."""

    def __init__(
        self,
        providers: tuple[ProviderAdapter, ...],
        policy: PolicyEngine,
        *,
        audit: AuditLog | None = None,
        stores: Callable[[str], CredentialStore] | None = None,
    ) -> None:
        self._providers = {provider.config.name: provider for provider in providers}
        if len(self._providers) != len(providers):
            raise ConfigurationError()
        self.policy = policy
        self.audit_log = audit if audit is not None else AuditLog()
        self._stores = stores if stores is not None else lambda kind: WindowsCredentialStore(kind)
        self._health: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._usage: dict[tuple[str, str, str], dict[str, int]] = {}
        self._lock = RLock()

    @classmethod
    def default(cls, profile: str = "default") -> AccessRuntime:
        return cls(
            (HTTPProvider(ProviderConfig("openai", "openai", profile=profile)),),
            PolicyEngine(
                (
                    Rule(
                        "console-read",
                        "cae-console",
                        "openai",
                        profile,
                        frozenset({"models", "health", "diagnostics", "usage"}),
                    ),
                )
            ),
        )

    def _provider(
        self,
        app: str,
        name: str,
        profile: str,
        operation: str,
        model: str | None = None,
        *,
        consume: bool = False,
    ) -> ProviderAdapter:
        for value in (app, name, profile):
            identifier(value)
        try:
            self.policy.authorize(app, name, profile, operation, model, consume=consume)
        except AccessDenied as exc:
            self.audit_log.emit(
                "policy_denied",
                app=app,
                provider=name,
                profile=profile,
                operation=operation
                if operation in {"models", "health", "chat", "embeddings", "diagnostics", "usage"}
                else "unknown",
                error_code=exc.code,
            )
            raise
        provider = self._providers.get(name)
        if provider is None or provider.config.profile != profile:
            self.audit_log.emit("policy_denied", app=app, provider=name, profile=profile)
            raise AccessDenied()
        return provider

    @correlated
    def execute(
        self, app: str, name: str, profile: str, operation: str, *,
        model: str | None = None, text: str | None = None, max_tokens: int = 256,
    ) -> dict[str, Any]:
        self._provider(app, name, profile, operation, model)
        try:
            with self.policy.request_slot(app, name, profile, operation, model):
                return self._execute(app, name, profile, operation, model=model,
                                     text=text, max_tokens=max_tokens)
        except ConcurrentLimitExceeded:
            self.audit_log.emit("policy_denied", app=app, provider=name,
                                profile=profile, operation=operation,
                                error_code=ConcurrentLimitExceeded.code)
            raise

    def _execute(
        self,
        app: str,
        name: str,
        profile: str,
        operation: str,
        *,
        model: str | None = None,
        text: str | None = None,
        max_tokens: int = 256,
    ) -> dict[str, Any]:
        provider = self._provider(app, name, profile, operation, model)
        actual = "models" if operation == "health" else operation
        if actual not in provider.capabilities:
            self.audit_log.emit(
                "request_failed", app=app, provider=name, profile=profile, operation=operation
            )
            raise UnsupportedOperation()
        if actual != "models" and (
            model is None
            or not MODEL.fullmatch(model)
            or not isinstance(text, str)
            or not 1 <= len(text) <= 100_000
        ):
            self.audit_log.emit(
                "request_failed", app=app, provider=name, profile=profile, operation=operation
            )
            raise ConfigurationError()
        if type(max_tokens) is not int or not 1 <= max_tokens <= 32768:
            raise ConfigurationError()
        self._provider(app, name, profile, operation, model, consume=True)
        self.audit_log.emit(
            "policy_granted", app=app, provider=name, profile=profile, operation=operation
        )
        secret = ""
        credential_failed = False
        if provider.config.authenticated:
            try:
                secret = self._stores(provider.config.kind).read(profile)
                validate_key(secret, provider.config.kind)
            except Exception:
                credential_failed = True
        if credential_failed:
            self.audit_log.emit(
                "credential_failed", app=app, provider=name, profile=profile, operation=operation
            )
            raise CredentialError()
        start = time.monotonic()
        safe: dict[str, Any] = {}
        failure: CAEError | None = None
        try:
            safe = redact(provider.request(actual, secret, model, text, max_tokens), secret)
        except APIError as exc:
            failure = APIError(exc.kind, exc.status)
        except UnsupportedOperation:
            failure = UnsupportedOperation()
        except Exception:
            failure = APIError("unavailable")
        finally:
            secret = ""
        elapsed = round((time.monotonic() - start) * 1000, 2)
        key = (app, name, profile)
        if failure is not None:
            self.audit_log.emit(
                "authentication_failed"
                if isinstance(failure, APIError) and failure.kind == "authentication"
                else "request_failed",
                app=app,
                provider=name,
                profile=profile,
                operation=operation,
                error_code=failure.code,
            )
            self.audit_log.emit(
                "provider_disconnected",
                app=app,
                provider=name,
                profile=profile,
                operation=operation,
            )
            with self._lock:
                self._health[key] = {
                    "api": "reachable"
                    if isinstance(failure, APIError) and failure.status
                    else "unavailable",
                    "authentication": "invalid"
                    if isinstance(failure, APIError) and failure.kind == "authentication"
                    else "unknown",
                    "latency_ms": elapsed,
                    "checked_at": datetime.now(UTC).isoformat(),
                }
            raise failure
        self.audit_log.emit(
            "request_completed", app=app, provider=name, profile=profile, operation=operation
        )
        self.audit_log.emit(
            "provider_connected", app=app, provider=name, profile=profile, operation=operation
        )
        with self._lock:
            self._health[key] = {
                "api": "available",
                "authentication": "valid" if provider.config.authenticated else "not_required",
                "latency_ms": elapsed,
                "checked_at": datetime.now(UTC).isoformat(),
            }
            counters = self._usage.setdefault(
                key, {"requests": 0, "input_tokens": 0, "output_tokens": 0}
            )
            counters["requests"] += 1
            usage = safe.get("usage", {})
            for field in ("input_tokens", "output_tokens"):
                value = usage.get(field, 0) if isinstance(usage, dict) else 0
                if type(value) is int and value >= 0:
                    counters[field] += value
        return safe

    def health(self, app: str, name: str, profile: str, *, probe: bool = False) -> dict[str, Any]:
        operation = "health" if probe else "diagnostics"
        provider = self._provider(app, name, profile, operation)
        error = None
        if probe:
            try:
                self.execute(app, name, profile, "health")
            except CAEError as exc:
                error = exc.code
        credential = "not_required"
        if provider.config.authenticated:
            try:
                credential = (
                    "stored" if self._stores(provider.config.kind).exists(profile) else "missing"
                )
            except Exception:
                credential = "unavailable"
        self.audit_log.emit(
            "health_read", app=app, provider=name, profile=profile, operation=operation
        )
        with self._lock:
            health = dict(
                self._health.get(
                    (app, name, profile),
                    {
                        "api": "unknown",
                        "authentication": "unknown",
                        "latency_ms": None,
                        "checked_at": None,
                    },
                )
            )
        if credential in {"missing", "unavailable"}:
            health["authentication"] = "unknown"
        return {
            "provider": name,
            "credential": credential,
            "broker": "ready",
            "broker_mode": "in_process",
            "policy": "ready",
            "error": error,
            **health,
        }

    def providers(self, app: str, profile: str) -> list[dict[str, Any]]:
        self.audit_log.emit("providers_read", app=app, profile=profile)
        return [
            {
                "name": name,
                "kind": provider.config.kind,
                "capabilities": sorted(provider.capabilities),
                "authenticated": provider.config.authenticated,
            }
            for name, provider in self._providers.items()
            if provider.config.profile == profile and self.policy.visible(app, name, profile)
        ]

    def usage(self, app: str, name: str, profile: str) -> dict[str, Any]:
        self._provider(app, name, profile, "usage")
        self.audit_log.emit("usage_read", app=app, provider=name, profile=profile)
        with self._lock:
            return {
                "scope": "runtime_observed",
                **self._usage.get(
                    (app, name, profile), {"requests": 0, "input_tokens": 0, "output_tokens": 0}
                ),
            }

    def policies(self, app: str) -> list[dict[str, Any]]:
        self.audit_log.emit("policies_read", app=app)
        return [rule.to_dict() for rule in self.policy.rules if rule.app == app]

    def audit(self, app: str) -> list[dict[str, Any]]:
        self.audit_log.emit("audit_read", app=app)
        return self.audit_log.events(app=app)

    def close(self) -> None:
        self.policy.ledger.close()
