import concurrent.futures
import threading
from dataclasses import replace

import pytest
from test_access_platform import runtime

from cae.errors import AccessDenied, ConcurrentLimitExceeded, ConfigurationError, RateLimitExceeded
from cae.policy import PolicyEngine, QuotaLedger, Rule


def limited(**values):
    return Rule("limit", "app", "openai", "default", frozenset({"models"}), **values)


def test_rate_limit_is_atomic_and_persistent(tmp_path):
    path = tmp_path / "quota.sqlite3"
    rule = limited(max_requests_per_minute=3)
    ledger = QuotaLedger(path, minute=lambda: "2026-10-11T12:00")

    def attempt(_):
        try:
            ledger.reserve((rule,))
            return True
        except RateLimitExceeded:
            return False

    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        assert sum(pool.map(attempt, range(20))) == 3
    ledger.close()
    ledger = QuotaLedger(path, minute=lambda: "2026-10-11T12:00")
    with pytest.raises(RateLimitExceeded):
        ledger.reserve((rule,))
    ledger.close()
    next_minute = QuotaLedger(path, minute=lambda: "2026-10-11T12:01")
    next_minute.reserve((rule,))
    next_minute.close()


def test_denied_rate_does_not_consume_other_rule_quota():
    ledger = QuotaLedger(minute=lambda: "2026-10-11T12:00")
    first = limited(max_requests_per_minute=1)
    second = replace(first, id="second", max_requests_per_day=1)
    ledger.reserve((first,))
    with pytest.raises(RateLimitExceeded):
        ledger.reserve((second, first))
    ledger.reserve((second,))
    ledger.close()


def test_concurrent_requests_stop_before_credential_or_provider(store):
    engine, access, transport = runtime(store)
    access.policy.ledger.close()
    access.policy = PolicyEngine((replace(access.policy.rules[0], max_concurrent_requests=1),))
    entered, release = threading.Event(), threading.Event()
    send = transport.send

    def blocked(*args):
        entered.set()
        assert release.wait(5)
        return send(*args)

    transport.send = blocked
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        future = pool.submit(engine.models)
        assert entered.wait(5)
        reads = store.reads
        try:
            with pytest.raises(ConcurrentLimitExceeded):
                engine.models()
            assert store.reads == reads
            assert transport.calls == []
        finally:
            release.set()
        assert future.result() == ["test-model"]
    assert engine.models() == ["test-model"]
    engine.close()


def test_rate_denial_precedes_provider_and_store(store):
    engine, access, transport = runtime(store)
    access.policy.ledger.close()
    access.policy = PolicyEngine((replace(access.policy.rules[0], max_requests_per_minute=1),),
        QuotaLedger(minute=lambda: "2026-10-11T12:00"))
    engine.models()
    reads, calls = store.reads, len(transport.calls)
    with pytest.raises(RateLimitExceeded):
        engine.models()
    assert store.reads == reads and len(transport.calls) == calls
    assert access.audit_log.events()[-1]["event"] == "policy_denied"
    engine.close()


def test_slots_release_after_exception_and_default_deny():
    policy = PolicyEngine((limited(max_concurrent_requests=1),))
    with pytest.raises(ValueError), policy.request_slot("app", "openai", "default", "models"):
        raise ValueError()
    with policy.request_slot("app", "openai", "default", "models"):
        pass
    with pytest.raises(AccessDenied), policy.request_slot("unknown", "openai", "default", "models"):
        pytest.fail("Unregistered application acquired a slot")
    policy.ledger.close()


@pytest.mark.parametrize("value", [True, 0, -1, 10_000_001, 1.5])
def test_limits_validate_types_and_range(value):
    with pytest.raises(ConfigurationError):
        limited(max_requests_per_minute=value)
    with pytest.raises(ConfigurationError):
        limited(max_concurrent_requests=value)
