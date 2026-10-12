"""Bounded local benchmark using an isolated synthetic store; no broker/credentials."""

import argparse
import json
import platform
import statistics
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from cae.audit import AuditLog, request_scope
from cae.audit_storage import Retention

ROOT = Path(__file__).resolve().parents[1]


def summary(samples: list[float]) -> dict[str, float]:
    return {"median_ms": round(statistics.median(samples), 3),
            "p95_ms": round(sorted(samples)[int((len(samples) - 1) * .95)], 3),
            "maximum_ms": round(max(samples), 3)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix="audit-performance-", dir=ROOT / ".tmp"))
    path = work / "managed/active.jsonl"
    limits = Retention(active_bytes=4096, total_bytes=16384, archive_count=3)
    audit = AuditLog(path, retention=limits)
    audit.emit("broker_started")

    def append(index: int) -> float:
        start = time.perf_counter()
        with request_scope():
            audit.emit("broker_status", app=f"test-{index}")
        return (time.perf_counter() - start) * 1000

    serial = [append(index) for index in range(100)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        concurrent = list(pool.map(append, range(100, 228)))
    start = time.perf_counter()
    recovered = AuditLog(path, retention=limits)
    status = recovered.storage_status()
    recovery_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    rows = recovered.events(include_archives=True)
    enumeration_ms = (time.perf_counter() - start) * 1000
    assert status["health"] == "ready" and status["archive_count"] == 3
    assert status["record_bytes"] <= limits.total_bytes
    assert len(rows) == len({row["event_id"] for row in rows})
    start = time.perf_counter()
    pruned = AuditLog(path, retention=Retention(active_bytes=4096, total_bytes=4096, archive_count=0))
    after = pruned.storage_status()
    cleanup_ms = (time.perf_counter() - start) * 1000
    assert after["archive_count"] == 0 and after["record_bytes"] <= 4096
    result: dict[str, Any] = {"result": "PASS", "platform": platform.platform(),
        "python": platform.python_version(), "events": 229, "worker_threads": 8,
        "serial_including_rotation": summary(serial), "concurrent_including_rotation": summary(concurrent),
        "startup_recovery_ms": round(recovery_ms, 3), "archive_enumeration_ms": round(enumeration_ms, 3),
        "three_archive_prune_ms": round(cleanup_ms, 3), "storage": status,
        "retained_events": len(rows), "isolated_state": str(work),
        "production_state_accessed": False, "power_loss_test": "NOT_RUN"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
