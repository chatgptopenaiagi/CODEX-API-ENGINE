"""Deny-overrides policy and atomic UTC-day quotas, optionally durable in SQLite."""

import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Literal

from .errors import (
    AccessDenied,
    ConcurrentLimitExceeded,
    ConfigurationError,
    QuotaExceeded,
    RateLimitExceeded,
)
from .security import identifier

OPERATIONS = frozenset({"models", "chat", "embeddings", "health", "diagnostics", "usage"})
MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    app: str
    provider: str
    profile: str
    operations: frozenset[str]
    effect: Literal["allow", "deny"] = "allow"
    models: frozenset[str] = frozenset()
    max_requests_per_day: int = 1000
    max_requests_per_minute: int | None = None
    max_concurrent_requests: int | None = None

    def __post_init__(self) -> None:
        for value in (self.id, self.app, self.provider, self.profile):
            identifier(value)
        object.__setattr__(self, "operations", frozenset(self.operations))
        object.__setattr__(self, "models", frozenset(self.models))
        if (
            self.effect not in {"allow", "deny"}
            or not self.operations
            or not self.operations <= OPERATIONS
        ):
            raise ConfigurationError()
        if (
            type(self.max_requests_per_day) is not int
            or not 1 <= self.max_requests_per_day <= 10_000_000
        ):
            raise ConfigurationError()
        if any(model != "*" and not MODEL.fullmatch(model) for model in self.models):
            raise ConfigurationError()
        for limit in (self.max_requests_per_minute, self.max_concurrent_requests):
            if limit is not None and (type(limit) is not int or not 1 <= limit <= 10_000_000):
                raise ConfigurationError()
        if self.effect == "allow" and self.operations & {"chat", "embeddings"} and not self.models:
            raise ConfigurationError()

    def matches(
        self, app: str, provider: str, profile: str, operation: str, model: str | None
    ) -> bool:
        if (self.app, self.provider, self.profile) != (
            app,
            provider,
            profile,
        ) or operation not in self.operations:
            return False
        if operation not in {"chat", "embeddings"}:
            return True
        return (
            (self.effect == "deny" and not self.models)
            or "*" in self.models
            or model in self.models
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["operations"] = sorted(self.operations)
        result["models"] = sorted(self.models)
        return result


class QuotaLedger:
    def __init__(self, path: Path | None = None, *, day: Callable[[], str] | None = None,
                 minute: Callable[[], str] | None = None) -> None:
        self._day = day if day is not None else lambda: datetime.now(UTC).date().isoformat()
        self._minute = minute or (lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M"))
        self._lock = RLock()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                raise ConfigurationError()
        self._db = sqlite3.connect(
            str(path) if path else ":memory:", timeout=5, check_same_thread=False
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS quotas (rule TEXT, day TEXT, count INTEGER NOT NULL, PRIMARY KEY(rule, day))"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS rates (rule TEXT, minute TEXT, count INTEGER NOT NULL, PRIMARY KEY(rule, minute))"
        )
        self._db.commit()

    def reserve(self, rules: tuple[Rule, ...]) -> None:
        failed = False
        exceeded = False
        rate_exceeded = False
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                day = self._day()
                minute = self._minute()
                for rule in rules:
                    row = self._db.execute(
                        "SELECT count FROM quotas WHERE rule=? AND day=?", (rule.id, day)
                    ).fetchone()
                    if row is not None and row[0] >= rule.max_requests_per_day:
                        exceeded = True
                        break
                    rate = self._db.execute(
                        "SELECT count FROM rates WHERE rule=? AND minute=?", (rule.id, minute)
                    ).fetchone()
                    if (rule.max_requests_per_minute is not None and rate is not None
                            and rate[0] >= rule.max_requests_per_minute):
                        rate_exceeded = True
                        break
                if exceeded or rate_exceeded:
                    self._db.rollback()
                else:
                    for rule in rules:
                        self._db.execute(
                            "INSERT INTO quotas VALUES (?, ?, 1) ON CONFLICT(rule, day) DO UPDATE SET count=count+1",
                            (rule.id, day),
                        )
                        self._db.execute(
                            "INSERT INTO rates VALUES (?, ?, 1) ON CONFLICT(rule, minute) DO UPDATE SET count=count+1",
                            (rule.id, minute),
                        )
                    # Keep the current and previous UTC date for clock-boundary recovery.
                    self._db.execute("DELETE FROM rates WHERE minute < date(?, '-1 day')", (day,))
                    self._db.commit()
            except Exception:
                try:
                    self._db.rollback()
                except sqlite3.Error:
                    pass
                failed = True
        if exceeded:
            raise QuotaExceeded()
        if rate_exceeded:
            raise RateLimitExceeded()
        if failed:
            raise AccessDenied()

    def close(self) -> None:
        with self._lock:
            self._db.close()


class PolicyEngine:
    def __init__(self, rules: tuple[Rule, ...], ledger: QuotaLedger | None = None) -> None:
        if len({rule.id for rule in rules}) != len(rules):
            raise ConfigurationError()
        self.rules = tuple(rules)
        self.ledger = ledger if ledger is not None else QuotaLedger()
        self._active: dict[str, int] = {}
        self._active_lock = RLock()

    @contextmanager
    def request_slot(self, app: str, provider: str, profile: str, operation: str,
                     model: str | None = None) -> Iterator[None]:
        self.authorize(app, provider, profile, operation, model, consume=False)
        matches = tuple(rule for rule in self.rules
                        if rule.matches(app, provider, profile, operation, model))
        with self._active_lock:
            if any(rule.max_concurrent_requests is not None
                   and self._active.get(rule.id, 0) >= rule.max_concurrent_requests
                   for rule in matches):
                raise ConcurrentLimitExceeded()
            for rule in matches:
                self._active[rule.id] = self._active.get(rule.id, 0) + 1
        try:
            yield
        finally:
            with self._active_lock:
                for rule in matches:
                    self._active[rule.id] -= 1

    def authorize(
        self,
        app: str,
        provider: str,
        profile: str,
        operation: str,
        model: str | None = None,
        *,
        consume: bool = True,
    ) -> None:
        matches = tuple(
            rule for rule in self.rules if rule.matches(app, provider, profile, operation, model)
        )
        if not matches or any(rule.effect == "deny" for rule in matches):
            raise AccessDenied()
        if consume:
            self.ledger.reserve(matches)

    def visible(self, app: str, provider: str, profile: str) -> bool:
        return any(
            rule.effect == "allow"
            and (rule.app, rule.provider, rule.profile) == (app, provider, profile)
            for rule in self.rules
        )
