"""Explicit administrator-owned TOML configuration. No credential values accepted."""

import tomllib
from pathlib import Path
from typing import Any

from .access import AccessRuntime
from .audit import AuditLog
from .audit_storage import Retention
from .errors import ConfigurationError
from .policy import PolicyEngine, QuotaLedger, Rule
from .providers import HTTPProvider, ProviderConfig
from .security import redact


def _keys(value: dict[str, Any], allowed: set[str]) -> None:
    if not isinstance(value, dict) or set(value) - allowed:
        raise ConfigurationError()


def audit_retention(text: str) -> Retention | None:
    """Missing section preserves legacy storage; explicit mode enables a fresh private store."""
    try:
        value = tomllib.loads(text).get("audit")
        if value is None:
            return None
        _keys(value, {"mode", "active_bytes", "total_bytes", "archive_count",
                      "archive_age_seconds", "lock_timeout_ms"})
        if value.get("mode") != "managed":
            raise ValueError()
        return Retention(**{key: item for key, item in value.items() if key != "mode"})
    except Exception:
        raise ConfigurationError() from None


def parse_config(text: str) -> tuple[tuple[ProviderConfig, ...], tuple[Rule, ...]]:
    invalid = False
    providers: tuple[ProviderConfig, ...] = ()
    rules: tuple[Rule, ...] = ()
    try:
        if len(text) > 128_000 or redact(text) != text:
            raise ValueError()
        value = tomllib.loads(text)
        _keys(value, {"schema_version", "providers", "rules", "audit"})
        if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
            raise ValueError()
        audit_retention(text)
        specs = []
        for item in value.get("providers", []):
            _keys(item, {"name", "kind", "endpoint", "profile", "authenticated"})
            if "authenticated" in item and type(item["authenticated"]) is not bool:
                raise ValueError()
            specs.append(ProviderConfig(**item))
        if not specs or len({spec.name for spec in specs}) != len(specs):
            raise ValueError()
        providers = tuple(specs)
        grants = []
        for item in value.get("rules", []):
            _keys(
                item,
                {
                    "id",
                    "app",
                    "provider",
                    "profile",
                    "operations",
                    "effect",
                    "models",
                    "max_requests_per_day",
                    "max_requests_per_minute",
                    "max_concurrent_requests",
                },
            )
            if not isinstance(item.get("operations"), list) or not isinstance(
                item.get("models", []), list
            ):
                raise ValueError()
            grants.append(Rule(**item))
        rules = tuple(grants)
        if len({rule.id for rule in rules}) != len(rules):
            raise ValueError()
        bindings = {(spec.name, spec.profile) for spec in specs}
        if any((rule.provider, rule.profile) not in bindings for rule in rules):
            raise ValueError()
    except Exception:
        invalid = True
    if invalid:
        raise ConfigurationError()
    return providers, rules


def load_runtime(path: Path) -> AccessRuntime:
    invalid = False
    text = ""
    try:
        if path.is_symlink() or path.stat().st_size > 128_000:
            raise ValueError()
        text = path.read_text(encoding="utf-8")
    except Exception:
        invalid = True
    if invalid:
        raise ConfigurationError()
    providers, rules = parse_config(text)
    state = path.resolve().parent / ".cae"
    retention = audit_retention(text)
    audit = AuditLog(state / "audit-managed" / "active.jsonl", retention=retention) if retention else AuditLog(state / "audit.jsonl")
    audit.emit("configuration_loaded")
    policy = PolicyEngine(rules, QuotaLedger(state / "quotas.sqlite3"))
    return AccessRuntime(tuple(HTTPProvider(spec) for spec in providers), policy, audit=audit)
