"""Bounded synthetic routing benchmark; no network, vault, or production broker."""

import argparse
import json
import platform
import statistics
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from cae.access import AccessRuntime
from cae.policy import ROUTING_MODES, PolicyEngine, Rule
from cae.providers import ProviderConfig
from cae.routing import CapabilityRequest
from cae.version import __version__


class MockProvider:
    config = ProviderConfig("local", "ollama", authenticated=False, routing_models=("synthetic",))
    capabilities = frozenset({"chat"})

    def request(self, operation: str, secret: str, model: str | None,
                text: str | None, max_tokens: int) -> dict[str, Any]:
        return {"text": "synthetic output"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    provider = MockProvider()
    runtime = AccessRuntime((provider,), PolicyEngine((Rule("sample", "app", "local", "default",
        frozenset({"chat"}), models=frozenset({"synthetic"}), routing_modes=ROUTING_MODES,
        max_requests_per_day=10000),)))
    request = {"contract_version": 1, "capability": "chat_generation", "model": "synthetic",
               "input": "synthetic", "routing_mode": "LOCAL_ONLY"}
    parsed = CapabilityRequest.parse(request)
    timings: dict[str, Any] = {}

    def measure(label: str, call: Any) -> None:
        samples = []
        for _ in range(200):
            start = time.perf_counter()
            call()
            samples.append((time.perf_counter() - start) * 1000)
        timings[label] = {"median_ms": statistics.median(samples), "p95_ms": sorted(samples)[189]}

    try:
        tracemalloc.start()
        measure("contract_validation", lambda: CapabilityRequest.parse(request))
        measure("authorization_candidate_filter", lambda: runtime.router._granted("app", provider, parsed))
        measure("availability_selection", lambda: runtime.router._available("app", provider, "synthetic"))
        measure("discovery_with_memory_audit", lambda: runtime.router.discover("app"))
        measure("full_routed_request_memory_audit", lambda: runtime.router.execute("app", request))
        start = time.perf_counter()
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(lambda _: runtime.router.execute("app", request), range(200)))
        elapsed = time.perf_counter() - start
        assert all(row["provider_id"] == "local" for row in results)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        report = {"version": __version__, "python": platform.python_version(),
                  "platform": platform.platform(), "provider": "MOCK_ONLY", "requests": 400,
                  "concurrent_requests": 200, "workers": 8, "concurrent_seconds": elapsed,
                  "requests_per_second": 200 / elapsed, "traced_current_bytes": current,
                  "traced_peak_bytes": peak, "timings": timings,
                  "limitations": "Single host microbenchmark, memory audit, not SLA or soak test"}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
