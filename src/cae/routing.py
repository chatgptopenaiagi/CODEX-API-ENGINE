"""Versioned capability selection; existing runtime owns authorization and execution."""

import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import TYPE_CHECKING, Any

from .audit import correlated
from .errors import AccessDenied, APIError, CAEError, ConfigurationError
from .policy import MODEL, ROUTING_MODES
from .providers import LOCAL, ProviderAdapter
from .security import identifier, redact

if TYPE_CHECKING:
    from .access import AccessRuntime

CAPABILITIES = {"chat_generation": "chat", "embeddings": "embeddings"}
CONTRACTS = {
    name: {"schema_version": 1, "operation": operation,
           "required_fields": ["contract_version", "capability", "model", "input", "routing_mode"],
           "optional_fields": ["provider", "allow_fallback", "max_tokens"],
           "max_input_characters": 8192, "max_output_tokens": 4096,
           "response_fields": ["contract_version", "capability", "provider_id", "model_id",
                               "result", "usage", "completion_status", "routing_metadata"],
           "result_field": "text" if name == "chat_generation" else "vectors",
           "cancellation": "NOT_SUPPORTED", "instructions": "single_untrusted_user_text",
           "usage_semantics": "reported_tokens_not_billing", "model_matching": "exact_operator_allowlist"}
    for name, operation in CAPABILITIES.items()
}
ROUTING_ERRORS = frozenset({"capability_unknown", "routing_policy_denied",
    "provider_unavailable", "request_outcome_unknown", "provider_response_invalid"})


class RoutingError(CAEError):
    def __init__(self, code: str) -> None:
        self.code = code if code in ROUTING_ERRORS else "routing_policy_denied"
        super().__init__()


@dataclass(frozen=True)
class CapabilityRequest:
    capability: str
    model: str
    input: str
    routing_mode: str
    provider: str | None = None
    allow_fallback: bool = False
    max_tokens: int = 256

    @classmethod
    def parse(cls, value: dict[str, Any]) -> CapabilityRequest:
        if (not isinstance(value, dict) or set(value) - {
                "contract_version", "capability", "model", "input", "routing_mode",
                "provider", "allow_fallback", "max_tokens"}
                or type(value.get("contract_version")) is not int
                or value["contract_version"] != 1):
            raise ConfigurationError()
        if not isinstance(value.get("capability"), str):
            raise ConfigurationError()
        if value["capability"] not in CAPABILITIES:
            raise RoutingError("capability_unknown")
        try:
            request = cls(**{k: v for k, v in value.items() if k != "contract_version"})
            if (not isinstance(request.model, str) or not MODEL.fullmatch(request.model)
                    or redact(request.model) != request.model
                    or not isinstance(request.input, str) or not 1 <= len(request.input) <= 8192
                    or not isinstance(request.routing_mode, str)
                    or request.routing_mode not in ROUTING_MODES
                    or type(request.allow_fallback) is not bool
                    or type(request.max_tokens) is not int or not 1 <= request.max_tokens <= 4096
                    or (request.routing_mode == "EXPLICIT_PROVIDER") != (request.provider is not None)
                    or (request.allow_fallback and request.routing_mode != "LOCAL_FIRST")):
                raise ValueError()
            if request.provider is not None:
                identifier(request.provider)
            request.input.encode("utf-8")
        except Exception:
            raise ConfigurationError() from None
        return request


def validated_result(capability: str, value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bound normalized adapter output without trusting injected adapters or usage."""
    try:
        if not isinstance(value, dict) or len(json.dumps(value, allow_nan=False).encode()) > 48000:
            raise ValueError()
        usage = value.get("usage", {})
        if not isinstance(usage, dict) or type(usage.get("reported", False)) is not bool:
            raise ValueError()
        for key in ("input_tokens", "output_tokens"):
            if key in usage and (type(usage[key]) is not int or not 0 <= usage[key] <= 10**12):
                raise ValueError()
        reported = (usage.get("reported") is True and "input_tokens" in usage
                    and (capability == "embeddings" or "output_tokens" in usage))
        accounting = {"state": "CONFIRMED_USAGE" if reported else "UNKNOWN_USAGE",
                      "input_tokens": usage.get("input_tokens") if reported else None,
                      "output_tokens": usage.get("output_tokens")
                      if reported and capability != "embeddings" else None,
                      "basis": "provider_reported" if reported else "unknown"}
        result: dict[str, Any]
        if capability == "chat_generation":
            text = value.get("text")
            if not isinstance(text, str) or not text or len(text) > 8192:
                raise ValueError()
            result = {"text": text}
        else:
            vectors = value.get("vectors")
            if (not isinstance(vectors, list) or len(vectors) != 1
                    or not isinstance(vectors[0], list) or not 1 <= len(vectors[0]) <= 4096
                    or any(type(x) not in {int, float} or not math.isfinite(x) for x in vectors[0])):
                raise ValueError()
            result = {"vectors": vectors}
    except Exception:
        raise RoutingError("provider_response_invalid") from None
    return result, accounting


class CapabilityRouter:
    """Immutable config, deterministic selection, no post-dispatch retry or network probes."""

    def __init__(self, runtime: AccessRuntime, providers: tuple[ProviderAdapter, ...],
                 *, clock: Callable[[], float] = time.monotonic) -> None:
        self.runtime = runtime
        self.providers = tuple(sorted(providers, key=lambda p: (p.config.routing_priority, p.config.name)))
        self.clock = clock
        self._failed: dict[tuple[str, str, str], float] = {}
        self._succeeded: dict[tuple[str, str, str], float] = {}
        self._lock = RLock()

    def _granted(self, app: str, provider: ProviderAdapter, request: CapabilityRequest) -> bool:
        config = provider.config
        operation = CAPABILITIES[request.capability]
        if (config.kind == "custom" or operation not in provider.capabilities
                or request.model not in config.routing_models):
            return False
        try:
            self.runtime.policy.authorize(app, config.name, config.profile, operation,
                                          request.model, consume=False)
        except AccessDenied:
            return False
        grants = [r for r in self.runtime.policy.rules
                  if r.matches(app, config.name, config.profile, operation, request.model)
                  and request.routing_mode in r.routing_modes]
        if not grants or (config.kind not in LOCAL and not all(r.allow_cloud for r in grants)):
            return False
        if request.allow_fallback and not all(r.allow_fallback for r in grants):
            return False
        return True

    def _available(self, app: str, provider: ProviderAdapter, model: str) -> bool:
        with self._lock:
            return (provider.config.routing_enabled
                    and self.clock() >= self._failed.get((app, provider.config.name, model), 0))

    def _availability(self, app: str, provider: ProviderAdapter, model: str) -> str:
        if not self._available(app, provider, model):
            return "UNAVAILABLE"
        with self._lock:
            if self._succeeded.get((app, provider.config.name, model), 0) > self.clock():
                return "AVAILABLE"
        return "UNKNOWN"

    @correlated
    def discover(self, app: str) -> dict[str, Any]:
        identifier(app)
        self.runtime.audit_log.emit("capabilities_read", app=app)
        declarations = []
        for provider in self.providers:
            for capability in CAPABILITIES:
                for model in provider.config.routing_models:
                    modes = [mode for mode in sorted(ROUTING_MODES)
                             if self._granted(app, provider, CapabilityRequest(
                                 capability, model, "discovery", mode))
                             and (mode != "LOCAL_ONLY" or provider.config.kind in LOCAL)
                             and (mode != "CLOUD_ONLY" or provider.config.kind not in LOCAL)]
                    if not modes:
                        continue
                    declarations.append({"capability": capability, "schema_version": 1,
                        "provider_id": provider.config.name, "adapter": provider.config.kind,
                        "model_id": model, "locality": "local" if provider.config.kind in LOCAL else "cloud",
                        "routing_modes": modes, "implemented": True, "configured": True,
                        "authorized": True, "availability": self._availability(app, provider, model), "live_validation": "NOT_ESTABLISHED",
                        "cancellation": "NOT_SUPPORTED", "usage": "provider_reported_or_unknown",
                        "input_classification": "untrusted_user_text"})
        return {"contract_version": 1, "capabilities": declarations[:64],
                "truncated": len(declarations) > 64,
                "contracts": {name: schema for name, schema in CONTRACTS.items()
                              if any(row["capability"] == name for row in declarations)}}

    @correlated
    def execute(self, app: str, value: dict[str, Any]) -> dict[str, Any]:
        identifier(app)
        request = CapabilityRequest.parse(value)
        candidates = [p for p in self.providers if self._granted(app, p, request)
                      and (request.provider is None or p.config.name == request.provider)
                      and (request.routing_mode != "LOCAL_ONLY" or p.config.kind in LOCAL)
                      and (request.routing_mode != "CLOUD_ONLY" or p.config.kind not in LOCAL)]
        metadata: dict[str, Any] = {"app": app, "capability": request.capability,
                    "routing_mode": request.routing_mode, "model": request.model}
        if not candidates:
            self.runtime.audit_log.emit("routing_denied", **metadata,
                                        error_code="routing_policy_denied")
            raise RoutingError("routing_policy_denied")
        if request.routing_mode == "LOCAL_FIRST":
            candidates.sort(key=lambda p: (p.config.kind not in LOCAL,
                                           p.config.routing_priority, p.config.name))
            if not request.allow_fallback:
                candidates = [p for p in candidates if p.config.kind in LOCAL]
        selected = next((p for p in candidates if self._available(app, p, request.model)), None)
        if selected is None:
            self.runtime.audit_log.emit("routing_denied", **metadata,
                                        error_code="provider_unavailable")
            raise RoutingError("provider_unavailable")
        config = selected.config
        fallback = request.routing_mode == "LOCAL_FIRST" and config.kind not in LOCAL
        self.runtime.audit_log.emit("route_selected", **metadata, provider=config.name,
                                    outcome="NOT_DISPATCHED", fallback=fallback)
        try:
            raw = self.runtime.execute(app, config.name, config.profile,
                CAPABILITIES[request.capability], model=request.model,
                text=request.input, max_tokens=request.max_tokens)
            result, usage = validated_result(request.capability, raw)
        except (APIError, RoutingError):
            with self._lock:
                now = self.clock()
                self._failed = {k: v for k, v in self._failed.items() if v > now}
                # Bounded advisory state. Eviction affects availability, never permissions.
                if len(self._failed) >= 1024:
                    self._failed.pop(next(iter(self._failed)))
                self._failed[(app, config.name, request.model)] = now + 5
            self.runtime.audit_log.emit("route_failed", **metadata, provider=config.name,
                                        outcome="DISPATCHED_OUTCOME_UNKNOWN", fallback=fallback,
                                        error_code="request_outcome_unknown")
            raise RoutingError("request_outcome_unknown") from None
        with self._lock:
            now = self.clock()
            self._succeeded = {k: v for k, v in self._succeeded.items() if v > now}
            if len(self._succeeded) >= 1024:
                self._succeeded.pop(next(iter(self._succeeded)))
            self._succeeded[(app, config.name, request.model)] = now + 5
        self.runtime.audit_log.emit("route_completed", **metadata, provider=config.name,
                                    outcome="COMPLETED", fallback=fallback)
        return {"contract_version": 1, "capability": request.capability,
                "provider_id": config.name, "model_id": request.model,
                "result": result, "usage": usage, "completion_status": "COMPLETED",
                "routing_metadata": {"mode": request.routing_mode, "fallback": fallback,
                                     "dispatches": 1, "provider_finish_reason": "UNKNOWN"}}
