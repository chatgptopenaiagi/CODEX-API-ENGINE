"""Adversarial real-pipe responses to all five compiled/installed clients."""

import ctypes
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from cae.pipe_transport import Pipe, process_peer

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    artifacts = ROOT / "dist/0.4.0-clients"
    integration = json.loads((artifacts / "CROSS-LANGUAGE-RESULTS.json").read_text())
    work = Path(integration["work"])
    testdir = work / "security"
    testdir.mkdir(exist_ok=True)
    peer = process_peer(os.getpid())
    env = dict(os.environ, NODE_PATH=str(work / "node/node_modules"),
               PSModulePath=str(artifacts / "powershell") + os.pathsep + os.environ.get("PSModulePath", ""))
    commands = {
        "python": [str(work / "venv/Scripts/python.exe"), "-I", str(ROOT / "integration-lab/python-client/main.py")],
        "dotnet": [str(artifacts / "dotnet-client/Lab.Client.exe")],
        "cpp": [str(artifacts / "CAE-Cpp-Client.exe")],
        "nodejs": [shutil.which("node") or "node", str(ROOT / "integration-lab/nodejs-client/main.js")],
        "powershell": [shutil.which("pwsh") or "pwsh", "-NoProfile", "-File",
                       str(ROOT / "integration-lab/powershell-client/main.ps1")],
    }
    cases = ["good", "wrong_pin", "wrong_image", "wrong_id", "wrong_version", "wrong_pid",
             "duplicate", "array_result", "error_redaction", "oversize", "timeout", "truncated"]
    results = []
    for language, command in commands.items():
        for case in cases:
            name = "cae-security-" + uuid4().hex
            descriptor = testdir / "client.json"
            descriptor.write_text(json.dumps({"pipe": name,
                "server_image": peer.image if case != "wrong_image" else str(ROOT / "missing.exe"),
                "server_sha256": peer.sha256 if case != "wrong_pin" else "0" * 64}), encoding="utf-8")
            env["CAE_CONNECTION_FILE"] = str(descriptor)
            pipe = Pipe.listener(name, peer.sid, first=True)
            stop = threading.Event()
            observed: list[bytes] = []

            def server(pipe: Pipe = pipe, stop: threading.Event = stop, case: str = case,
                       observed: list[bytes] = observed) -> None:
                try:
                    pipe.accept(stop)
                    raw = pipe.receive(3)
                    observed.append(raw)
                    request = json.loads(raw)
                    response: dict[str, Any] = {"v": 1, "id": request["id"], "ok": True,
                        "result": {}, "error": None, "broker_pid": peer.pid}
                    if case == "wrong_id":
                        response["id"] = "0" * 32
                    if case == "wrong_version":
                        response["v"] = 2
                    if case == "wrong_pid":
                        response["broker_pid"] = peer.pid + 1
                    if case == "array_result":
                        response["result"] = []
                    if case == "error_redaction":
                        response.update(ok=False, error="DO_NOT_DISCLOSE_SYNTHETIC_ERROR")
                    body = json.dumps(response).encode()
                    if case == "duplicate":
                        body = body[:-1] + b',"v":1}'
                    if case == "oversize":
                        # Deliberately bypass safe send framing for a hostile test server.
                        pipe._io("write", ctypes.create_string_buffer((65537).to_bytes(4, "little")),
                                 4, time.monotonic() + 2)
                        pipe.receive(2)
                        return
                    if case == "timeout":
                        stop.wait(1.5)
                        return
                    if case == "truncated":
                        pipe._io("write", ctypes.create_string_buffer(
                            (100).to_bytes(4, "little") + b"{}"), 6, time.monotonic() + 2)
                        return
                    pipe.send(body)
                    pipe.receive(2)
                except Exception:
                    pass
                finally:
                    pipe.close()

            thread = threading.Thread(target=server)
            thread.start()
            started = time.monotonic()
            try:
                probe = "probe" if language == "powershell" else "--probe"
                completed = subprocess.run([*command, probe], env=env, cwd=work,
                    capture_output=True, timeout=15)
                answer = completed.stdout.decode("utf-8-sig").strip()
                elapsed = time.monotonic() - started
                assert completed.returncode == 0, (language, case, "process_failed")
                expected = {"good": {"ok"}, "wrong_pin": {"broker_unavailable"},
                    "wrong_image": {"broker_unavailable"}, "timeout": {"broker_unavailable"},
                    "truncated": {"broker_unavailable"}, "error_redaction": {"broker_request_failed"}}
                assert answer in expected.get(case, {"invalid_protocol"}), (language, case, "unexpected_code")
                assert b"DO_NOT_DISCLOSE" not in completed.stdout + completed.stderr
                if case in {"wrong_pin", "wrong_image"}:
                    assert not observed, (language, case, "sent_before_authentication")
                results.append({"language": language, "case": case, "result": "passed",
                                "seconds": round(elapsed, 3)})
            finally:
                stop.set()
                thread.join(timeout=5)
                assert not thread.is_alive()
    (artifacts / "CLIENT-SECURITY-RESULTS.json").write_text(json.dumps(results, indent=2))
    print(json.dumps({"security_cases_passed": len(results), "languages": 5}))


if __name__ == "__main__":
    main()
