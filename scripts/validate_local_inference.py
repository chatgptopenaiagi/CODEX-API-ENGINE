"""Explicit real llama.cpp acceptance; isolated source broker, no production state.

Run only with an operator-approved, already running loopback server/model.
No downloads, server changes, cloud requests, or provider response bodies in audit.
"""

import argparse
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

from cae import BrokerClient
from cae.broker_client import BrokerRemoteError
from cae.pipe_transport import IPCError, process_peer

ROOT = Path(__file__).resolve().parents[1]
MODEL = r"I:\LocalAI\models\Qwen3-4B-Q4_K_M\Qwen3-4B-Q4_K_M.gguf"
PROMPT = "Reply with exactly: Local AI inference is operational."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-approved-local", action="store_true")
    args = parser.parse_args()
    if not args.run_approved_local:
        parser.error("explicit --run-approved-local required")
    work = ROOT / ".tmp" / ("m3-local-" + uuid4().hex)
    work.mkdir(parents=True)
    report: dict[str, Any] = {"endpoint": "http://127.0.0.1:8080", "model": MODEL,
        "server": "llama.cpp (operator identified)", "adapter": "vllm-compatible wire contract",
        "broker_build": "source subprocess", "work": str(work), "checks": {}}
    checks = report["checks"]
    # Only the explicitly approved endpoint; no proxies or redirects.
    connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=30)
    connection.request("GET", "/v1/models")
    response = connection.getresponse()
    body = response.read(65537)
    assert response.status == 200 and len(body) <= 65536
    assert MODEL in [row["id"] for row in json.loads(body)["data"]]
    connection.close()
    checks["real_model_discovery"] = "PASS"
    # Diagnose short-output behavior without storing/printing reasoning text.
    connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=30)
    connection.request("POST", "/v1/chat/completions", json.dumps({"model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 32,
        "temperature": 0, "stream": False}), {"Content-Type": "application/json"})
    response = connection.getresponse()
    body = response.read(262145)
    assert response.status == 200 and len(body) <= 262144
    data = json.loads(body)
    choice = data["choices"][0]
    report["short_output_probe"] = {"max_tokens": 32, "finish_reason": choice.get("finish_reason"),
        "content_characters": len(choice["message"].get("content") or ""),
        "reasoning_characters": len(choice["message"].get("reasoning_content") or ""),
        "usage": data.get("usage"), "fingerprint": data.get("system_fingerprint")}
    del data, body, choice
    connection.close()
    peer = process_peer(os.getpid())
    enrollment = {"app": "local-test", "image": peer.image, "sha256": peer.sha256, "admin": False}
    runtime = work / "runtime.toml"
    runtime.write_text('schema_version=1\n[audit]\nmode="managed"\n'
        'active_bytes=4096\ntotal_bytes=131072\narchive_count=32\n[[providers]]\nname="llamacpp"\n'
        'kind="vllm"\nendpoint="http://127.0.0.1:8080"\nauthenticated=false\n'
        f'routing_models=[{json.dumps(MODEL)}]\n[[rules]]\nid="local-test"\n'
        'app="local-test"\nprovider="llamacpp"\nprofile="default"\n'
        'operations=["chat"]\nrouting_modes=["LOCAL_ONLY"]\n'
        f'models=[{json.dumps(MODEL)}]\nmax_requests_per_day=5\n'
        'max_concurrent_requests=1\nallow_cloud=false\nallow_fallback=false\n', encoding="utf-8")
    config = work / "broker.json"
    settings = {"version": 1, "pipe": "cae-m3-" + uuid4().hex, "runtime": str(runtime),
        "server": dict(enrollment, app="broker"), "clients": [enrollment]}

    def save() -> None:
        replacement = work / "broker.next"
        replacement.write_text(json.dumps(settings), encoding="utf-8")
        os.replace(replacement, config)

    save()
    client = BrokerClient(settings["pipe"], peer.image, peer.sha256)
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    process = subprocess.Popen([sys.executable, "-m", "cae.broker_service", "--config", str(config)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW)

    def denied(call: Any, code: str) -> None:
        try:
            call()
        except BrokerRemoteError as exc:
            assert exc.code == code
        else:
            raise AssertionError("expected_denial")

    def route() -> dict[str, Any]:
        return client.route("chat_generation", MODEL, PROMPT, max_tokens=256)

    try:
        for _ in range(100):
            try:
                status = client.get_status()
                break
            except Exception:
                assert process.poll() is None, "isolated_broker_start_failed"
                time.sleep(.1)
        else:
            raise AssertionError("isolated_broker_start_timeout")
        assert status["broker_pid"] != os.getpid() and status["app"] == "local-test"
        report["broker_pid"] = status["broker_pid"]
        report["launcher_pid"] = process.pid
        checks["authenticated_independent_process"] = "PASS"
        denied(client.stop, "access_denied")
        denied(lambda: client.route("chat_generation", MODEL, PROMPT, routing_mode="CLOUD_ONLY"),
               "routing_policy_denied")
        denied(lambda: client.route("chat_generation", "unapproved", PROMPT), "routing_policy_denied")
        checks["cloud_model_and_admin_denial"] = "PASS"
        start = time.monotonic()
        result = route()
        assert result["model_id"] == MODEL and result["provider_id"] == "llamacpp"
        assert result["result"]["text"].strip() and result["usage"]["state"] == "CONFIRMED_USAGE"
        assert "reasoning" not in json.dumps(result)
        report["routed_response"] = result  # Synthetic final content only.
        report["routed_latency_ms"] = round((time.monotonic() - start) * 1000, 2)
        checks["real_routed_inference"] = "PASS"
        # Synchronize while the real call holds its concurrency reservation.
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(route)
            time.sleep(.15)
            denied(route, "concurrent_request_limit")
            assert future.result()["result"]["text"]
        checks["real_concurrency_limit"] = "PASS"
        impatient = BrokerClient(settings["pipe"], peer.image, peer.sha256, timeout=.01)
        try:
            impatient.route("chat_generation", MODEL, PROMPT, max_tokens=256)
        except IPCError:
            checks["client_timeout"] = "PASS"
        else:
            raise AssertionError("expected_client_timeout")
        # A timeout is not cancellation: wait for the accepted worker, never replay it.
        for _ in range(300):
            if client.get_status()["active_connections"] <= 1:
                break
            time.sleep(.1)
        else:
            raise AssertionError("provider_worker_did_not_finish")
        route()
        route()
        denied(route, "daily_request_limit")
        checks["real_quota_limit"] = "PASS"
        # Operator edits only this disposable enrollment; an unrecognized hash revokes next call.
        settings["clients"] = [dict(enrollment, sha256="0" * 64)]
        save()
        denied(client.get_status, "access_denied")
        checks["revocation_next_connection"] = "PASS"
        settings["clients"] = [dict(enrollment, admin=True)]
        save()
        client.stop()
        assert process.wait(timeout=15) == 0
        checks["clean_shutdown"] = "PASS"
        audit = "".join(p.read_text(encoding="utf-8") for p in
                        (work / ".cae" / "audit-managed").glob("*.jsonl"))
        assert PROMPT not in audit and "reasoning_content" not in audit
        assert result["result"]["text"] not in audit
        rows = [json.loads(line) for line in audit.splitlines()]
        completed = [row for row in rows if row["event"] == "route_completed"]
        assert len(completed) == 5, "expected_exactly_five_dispatches_including_timed_out_client"
        report["completed_provider_dispatches"] = len(completed)
        checks["timeout_no_replay_or_cancellation_claim"] = "PASS"
        report["audit_sha256"] = hashlib.sha256(audit.encode()).hexdigest()
        checks["audit_content_exclusion"] = "PASS"
    finally:
        if process.poll() is None:
            settings["clients"] = [dict(enrollment, admin=True)]
            save()
            try:
                client.stop()
                process.wait(timeout=35)
            except Exception:
                process.terminate()  # Only the exact isolated child created above.
                process.wait(timeout=10)
        report["isolated_broker_exit"] = process.returncode
        (work / "RESULTS.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"report": str(work / "RESULTS.json"), "checks": checks}))


if __name__ == "__main__":
    main()
