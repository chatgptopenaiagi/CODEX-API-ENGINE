"""Packaged broker acceptance: optional approved Qwen call, isolated endpoint failures.

Real-server outage injection is forbidden. Faults affect only a subprocess created
by this harness on an OS-assigned loopback port. Reports contain synthetic data only.
"""

import argparse
import ctypes
import hashlib
import http.client
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

from cae import BrokerClient, __version__
from cae.audit import AuditLog
from cae.broker_client import BrokerRemoteError
from cae.config import audit_retention
from cae.pipe_transport import IPCError, process_peer

ROOT = Path(__file__).resolve().parents[1]
MODEL = r"I:\LocalAI\models\Qwen3-4B-Q4_K_M\Qwen3-4B-Q4_K_M.gguf"
PROMPT = "Reply with exactly: Local AI inference is operational."


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(".next")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def resources(pid: int) -> dict[str, int]:
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                    *[(name, ctypes.c_size_t) for name in ("peak", "working", "pool_peak", "pool",
                       "nonpaged_peak", "nonpaged", "pagefile", "pagefile_peak", "private")]]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.GetProcessHandleCount.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    handle = kernel.OpenProcess(0x0400 | 0x0010, False, pid)
    assert handle
    try:
        count = ctypes.c_ulong()
        info = Counters()
        info.cb = ctypes.sizeof(info)
        assert kernel.GetProcessHandleCount(handle, ctypes.byref(count))
        assert psapi.GetProcessMemoryInfo(handle, ctypes.byref(info), info.cb)
        return {"handles": count.value, "working_bytes": info.working, "private_bytes": info.private}
    finally:
        kernel.CloseHandle(handle)


class Lab:
    def __init__(self, work: Path, broker: Path, console: Path, endpoint: str,
                 *, daily: int = 100, minute: int = 100) -> None:
        self.work, self.broker, self.console = work, broker, console
        work.mkdir()
        peer = process_peer(os.getpid())
        self.enrollment = {"app": "lab", "image": peer.image, "sha256": peer.sha256, "admin": False}
        self.console_enrollment = {"app": "console", "image": str(console),
                                   "sha256": digest(console), "admin": False}
        self.runtime = work / "runtime.toml"
        provider = ('schema_version=1\n[audit]\nmode="managed"\nactive_bytes=4096\n'
            'total_bytes=262144\narchive_count=32\n[[providers]]\nname="local"\nkind="vllm"\n'
            f'endpoint={json.dumps(endpoint)}\nauthenticated=false\nrouting_models=[{json.dumps(MODEL)}]\n')
        rules = "".join(f'[[rules]]\nid="{app}"\napp="{app}"\nprovider="local"\n'
            'profile="default"\noperations=["chat"]\nrouting_modes=["LOCAL_ONLY"]\n'
            f'models=[{json.dumps(MODEL)}]\nmax_requests_per_day={daily}\n'
            f'max_requests_per_minute={minute}\nmax_concurrent_requests=1\n'
            'allow_cloud=false\nallow_fallback=false\n' for app in ("lab", "console"))
        self.runtime.write_text(provider + rules, encoding="utf-8")
        self.settings = {"version": 1, "pipe": "cae-m3-packaged-" + uuid4().hex,
            "runtime": str(self.runtime), "server": {"app": "broker", "image": str(broker),
            "sha256": digest(broker), "admin": False}, "clients": [self.enrollment]}
        self.config = work / "broker.json"
        self.save()
        descriptor = {"pipe": self.settings["pipe"], "server_image": str(broker),
                      "server_sha256": digest(broker)}
        write_json(work / "connection.json", descriptor)
        self.client = BrokerClient(**descriptor)
        self.process: subprocess.Popen[bytes] | None = None
        self.pid = 0

    def save(self) -> None:
        write_json(self.config, self.settings)

    def start(self) -> dict[str, Any]:
        self.process = subprocess.Popen([str(self.broker), "--config", str(self.config)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(150):
            try:
                status = self.client.get_status()
                assert status["version"] == __version__
                self.pid = status["broker_pid"]
                return status
            except IPCError:
                assert self.process.poll() is None, "isolated_broker_exited"
                time.sleep(.1)
        raise AssertionError("isolated_broker_start_timeout")

    def stop(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        prior = self.settings["clients"]
        self.settings["clients"] = [dict(self.enrollment, admin=True), self.console_enrollment]
        self.save()
        try:
            self.client.stop()
            assert self.process.wait(timeout=40) == 0
        finally:
            self.settings["clients"] = prior
            self.save()
            if self.process.poll() is None:
                # Exact process tree owned by this harness; never query/kill by executable name.
                subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                               capture_output=True, timeout=10)

    def route(self, **extra: Any) -> dict[str, Any]:
        return self.client.route("chat_generation", MODEL, PROMPT, max_tokens=256, **extra)

    def denied(self, code: str, **extra: Any) -> None:
        start = time.monotonic()
        try:
            self.route(**extra)
        except BrokerRemoteError as exc:
            assert exc.code == code, ("unexpected_error_code", exc.code)
        else:
            raise AssertionError("expected_denial")
        assert time.monotonic() - start < 30

    def console_call(self) -> tuple[int, dict[str, Any]]:
        request = {"contract_version": 1, "capability": "chat_generation", "model": MODEL,
                   "input": PROMPT, "routing_mode": "LOCAL_ONLY", "max_tokens": 256}
        write_json(self.work / "request.json", request)
        report = self.work / ("console-" + uuid4().hex + ".json")
        result = subprocess.run([str(self.console), "--connection", str(self.work / "connection.json"),
            "--route-request", str(self.work / "request.json"), "--report", str(report)],
            capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        return result.returncode, json.loads(report.read_text(encoding="utf-8"))

    def audit(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        audit = AuditLog(self.work / ".cae/audit-managed/active.jsonl",
                         retention=audit_retention(self.runtime.read_text()))
        rows = audit.events(include_archives=True)
        serialized = json.dumps(rows)
        assert PROMPT not in serialized and "PRIVATE_REASONING_CANARY" not in serialized
        assert "reasoning_content" not in serialized and "sk-synthetic" not in serialized
        # Startup/configuration events are not requests and legitimately have no ID.
        requests = [row for row in rows if row["event"].startswith(("route_", "ipc_"))]
        assert requests and all(row.get("request_id") for row in requests)
        completed = [row for row in rows if row["event"] == "route_completed"]
        assert completed
        related = {row["event"] for row in rows if row["request_id"] == completed[-1]["request_id"]}
        assert {"ipc_authenticated", "route_selected", "policy_granted",
                "request_completed", "route_completed"} <= related
        status = audit.storage_status()
        assert status["health"] == "ready" and status["record_bytes"] <= 262144
        return rows, status


class Endpoint:
    def __init__(self, work: Path) -> None:
        self.work = work
        work.mkdir()
        self.port = 0
        self.process: subprocess.Popen[bytes] | None = None
        self.mode("valid")

    def mode(self, value: str) -> None:
        temporary = self.work / "mode.next"
        temporary.write_text(value)
        os.replace(temporary, self.work / "mode.txt")

    def calls(self) -> int:
        path = self.work / "calls.jsonl"
        return len(path.read_text().splitlines()) if path.exists() else 0

    def start(self) -> None:
        ready = self.work / "ready.json"
        if ready.exists():
            ready.rename(self.work / ("ready-" + uuid4().hex + ".json"))
        self.process = subprocess.Popen([sys.executable, str(ROOT / "scripts/m3_recovery_endpoint.py"),
            "--state", str(self.work), "--port", str(self.port)], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(100):
            if ready.exists():
                self.port = json.loads(ready.read_text())["port"]
                assert self.port != 8080
                return
            assert self.process.poll() is None
            time.sleep(.05)
        raise AssertionError("disposable_endpoint_start_timeout")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            # venv launcher may have a Python child; terminate exactly our isolated tree.
            subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                           capture_output=True, check=True, timeout=10)
            self.process.wait(timeout=10)


def recover(lab: Lab, endpoint: Endpoint) -> None:
    endpoint.mode("valid")
    time.sleep(5.1)  # Documented bounded advisory unhealthy cache, not an operation replay.
    value = lab.route()
    assert value["result"]["text"] == "SYNTHETIC_FINAL"
    assert value["routing_metadata"]["dispatches"] == 1
    assert not value["routing_metadata"]["fallback"]


def mock_acceptance(work: Path, broker: Path, console: Path, result: dict[str, Any]) -> dict[str, Any]:
    endpoint = Endpoint(work / "endpoint")
    endpoint.start()
    endpoint.stop()
    lab = Lab(work / "mock-broker", broker, console, f"http://127.0.0.1:{endpoint.port}")
    result.update(classification="MOCK_ONLY", cases=[])
    try:
        lab.start()
        initial = resources(lab.pid)
        lab.denied("request_outcome_unknown")
        endpoint.start()
        recover(lab, endpoint)
        result["cases"].append("unavailable_then_start")
        # Kill only our disposable server while it owns an in-flight request.
        endpoint.mode("terminate")
        before = endpoint.calls()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(lab.denied, "request_outcome_unknown")
            for _ in range(100):
                if endpoint.calls() > before:
                    break
                time.sleep(.05)
            else:
                raise AssertionError("request_never_dispatched")
            assert lab.client.get_status()["broker_pid"] == lab.pid
            endpoint.stop()
            pending.result(timeout=30)
        endpoint.start()
        recover(lab, endpoint)
        result["cases"].append("mid_request_termination_then_restart")
        for mode in ("reset", "json", "missing", "wrong_type", "wrong_model", "usage",
                     "oversized_output", "oversized_body", "error", "truncated", "provider_timeout"):
            endpoint.mode(mode)
            before = endpoint.calls()
            start = time.monotonic()
            lab.denied("request_outcome_unknown")
            assert endpoint.calls() == before + 1, "unexpected_retry"
            result["cases"].append({"fault": mode, "bounded_failure_ms": round((time.monotonic()-start)*1000, 2)})
            recover(lab, endpoint)
        # Late response completes the accepted request; next request has distinct content/correlation.
        endpoint.mode("late")
        impatient = BrokerClient(lab.client.pipe, str(broker), digest(broker), timeout=.05)
        try:
            impatient.route("chat_generation", MODEL, PROMPT)
        except IPCError:
            pass
        else:
            raise AssertionError("client_did_not_timeout")
        lab.denied("concurrent_request_limit")
        time.sleep(2)
        endpoint.mode("valid")
        assert lab.route()["result"]["text"] == "SYNTHETIC_FINAL"
        result["cases"].append("client_timeout_late_response_slot_release")
        # Warm the fixed worker set before comparing resource use across outages.
        for _ in range(16):
            lab.route()
        warmed = resources(lab.pid)
        for _ in range(3):
            endpoint.stop()
            lab.denied("request_outcome_unknown")
            endpoint.start()
            recover(lab, endpoint)
        result["cases"].append("three_outage_restart_cycles")
        result["same_process_resource_sample"] = {"initial": initial, "warmed_before_cycles": warmed,
                                                  "after_cycles": resources(lab.pid)}
        before = endpoint.calls()
        try:
            lab.client.route("chat_generation", "unapproved-model", PROMPT)
        except BrokerRemoteError as exc:
            assert exc.code == "routing_policy_denied"
        else:
            raise AssertionError("unapproved_model_allowed")
        assert endpoint.calls() == before
        # Unenrolled packaged client, then allow and revoke, preserving revocation across restart.
        code, body = lab.console_call()
        assert code == 2 and body == {"error": "access_denied"}
        lab.settings["clients"].append(lab.console_enrollment)
        lab.save()
        code, body = lab.console_call()
        assert code == 0 and body["response"]["result"]["text"] == "SYNTHETIC_FINAL"
        lab.settings["clients"] = [lab.enrollment]
        lab.save()
        assert lab.console_call() == (2, {"error": "access_denied"})
        old_pid = lab.pid
        lab.stop()
        lab.start()
        assert lab.pid != old_pid
        assert lab.console_call() == (2, {"error": "access_denied"})
        assert lab.route()["result"]["text"] == "SYNTHETIC_FINAL"
        result["cases"].append("packaged_client_enrollment_revocation_broker_restart")
        before = endpoint.calls()
        lab.denied("routing_policy_denied", routing_mode="CLOUD_ONLY")
        assert endpoint.calls() == before
        final = resources(lab.pid)
        result.update(initial_resources=initial, final_after_restart_resources=final,
                      endpoint_calls=endpoint.calls(), final_broker_pid=lab.pid)
        lab.stop()
        rows, storage = lab.audit()
        assert any(r["event"] == "route_failed" for r in rows)
        assert any(r["event"] == "route_completed" for r in rows)
        assert storage["rotation_ns"] > 0
        result.update(audit_storage=storage, retained_events=len(rows))
        # Separate persistent quota/rate cases; failed dispatch consumes a reservation.
        for name, limits, expected in (("daily", {"daily": 2}, "daily_request_limit"),
                                       ("minute", {"minute": 1}, "request_rate_limit")):
            if name == "minute" and time.time() % 60 > 45:
                time.sleep(60 - time.time() % 60 + .1)
            bounded = Lab(work / name, broker, console, f"http://127.0.0.1:{endpoint.port}", **limits)
            try:
                bounded.start()
                if name == "daily":
                    endpoint.mode("error")
                    bounded.denied("request_outcome_unknown")
                    recover(bounded, endpoint)
                else:
                    bounded.route()
                before = endpoint.calls()
                bounded.denied(expected)
                bounded.stop()
                bounded.start()
                bounded.denied(expected)
                assert endpoint.calls() == before
                result["cases"].append(name + "_quota_survives_restart")
            finally:
                bounded.stop()
        return result
    finally:
        lab.stop()
        endpoint.stop()


def real_acceptance(work: Path, broker: Path, console: Path) -> dict[str, Any]:
    connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=5)
    try:
        connection.request("GET", "/v1/models")
        response = connection.getresponse()
        data = response.read(65537)
        if response.status != 200 or len(data) > 65536:
            return {"status": "REAL_QWEN_UNAVAILABLE"}
        assert MODEL in [row["id"] for row in json.loads(data)["data"]]
    except OSError:
        return {"status": "REAL_QWEN_UNAVAILABLE"}
    finally:
        connection.close()
    lab = Lab(work / "real-broker", broker, console, "http://127.0.0.1:8080", daily=1)
    try:
        lab.settings["clients"].append(lab.console_enrollment)
        lab.save()
        status = lab.start()
        lab.denied("routing_policy_denied", routing_mode="CLOUD_ONLY")
        start = time.monotonic()
        code, response = lab.console_call()
        elapsed = round((time.monotonic()-start)*1000, 2)
        assert code == 0, "real_packaged_inference_failed"
        value = response["response"]
        assert response["status"]["version"] == __version__
        assert response["status"]["broker_pid"] == status["broker_pid"]
        assert response["status"]["app"] == "console"
        assert value["model_id"] == MODEL and value["provider_id"] == "local"
        assert value["result"]["text"].strip() and "reasoning" not in json.dumps(value)
        assert value["routing_metadata"]["mode"] == "LOCAL_ONLY"
        assert value["routing_metadata"]["fallback"] is False
        # Second call must fail at quota; it must not create a second real inference.
        assert lab.console_call() == (2, {"error": "daily_request_limit"})
        lab.stop()
        rows, storage = lab.audit()
        completed = [row for row in rows if row["event"] == "route_completed"]
        assert len(completed) == 1
        assert value["result"]["text"] not in json.dumps(rows)
        return {"status": "PASS", "classification": "REAL_LOCAL_PROVIDER_PACKAGED_BROKER_AND_CLIENT",
            "broker_status": status, "client_status": response["status"],
            "response": value, "client_process_total_ms": elapsed,
            "request_id": completed[0]["request_id"], "audit_storage": storage,
            "real_inference_dispatches": 1, "real_server_restart": "NOT_RUN"}
    finally:
        lab.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-directory", type=Path, required=True)
    parser.add_argument("--real-qwen", action="store_true", help="One approved bounded real inference")
    args = parser.parse_args()
    directory = args.broker_directory.resolve()
    expected = {row["File"]: row["Hash"].lower() for row in
                json.loads((directory / "SHA256SUMS.json").read_text(encoding="utf-8-sig"))}
    broker, console = directory / "CAE-Broker.exe", directory / "CAE-Console-Client.exe"
    assert digest(broker) == expected[broker.name] and digest(console) == expected[console.name]
    work = ROOT / ".tmp" / ("m3-packaged-" + uuid4().hex)
    work.mkdir()
    report: dict[str, Any] = {"broker": str(broker), "broker_sha256": digest(broker),
        "console_sha256": digest(console), "work": str(work), "version": __version__}
    try:
        report["mock"] = {}
        mock_acceptance(work, broker, console, report["mock"])
        report["real"] = real_acceptance(work, broker, console) if args.real_qwen else {"status": "NOT_RUN"}
        report["status"] = "PASS"
    finally:
        write_json(work / "RESULTS.json", report)
        print(json.dumps({"report": str(work / "RESULTS.json"), "status": report.get("status", "FAIL")}))


if __name__ == "__main__":
    main()
