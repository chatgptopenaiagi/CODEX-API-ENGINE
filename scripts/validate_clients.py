"""Real cross-language processes against one unchanged v0.3.1 broker; mock HTTP only."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

from cae import BrokerClient
from cae.pipe_transport import process_peer

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = "sk-" + "synthetic-leak-canary-" * 4


class MockProvider(BaseHTTPRequestHandler):
    calls = 0
    posts = 0

    def do_POST(self) -> None:
        type(self).posts += 1
        self.send_error(403)

    def do_GET(self) -> None:
        assert self.path == "/v1/models"
        assert "Authorization" not in self.headers
        type(self).calls += 1
        body = json.dumps({"data": [{"id": "lab-model"}, {"id": SYNTHETIC}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: Any) -> None:
        pass


def run(command: list[str], env: dict[str, str], *, cwd: Path = ROOT) -> None:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError("validation_subprocess_failed: " + Path(command[0]).name)


def wait_reports(paths: dict[str, Path], *, expected_pid: int | None = None,
                 after: float = 0) -> dict[str, Any]:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        values = {}
        try:
            for name, path in paths.items():
                data = path.read_text(encoding="utf-8-sig")
                assert SYNTHETIC not in data
                value = json.loads(data)
                assert value["denied"] and value["malformed"] and value["restricted"]
                assert value["status"]["app"] == name
                assert value["status"]["broker_mode"] == "named_pipe"
                assert "lab-model" in str(value["models"])
                assert path.stat().st_mtime > after
                assert expected_pid is None or value["status"]["broker_pid"] == expected_pid
                values[name] = value
            assert len({v["status"]["broker_pid"] for v in values.values()}) == 1
            return values
        except (OSError, ValueError, AssertionError, KeyError):
            time.sleep(0.2)
    raise RuntimeError("cross_language_acceptance_timeout")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=ROOT / "dist/0.4.0-clients")
    parser.add_argument("--electron", type=Path, help="Optional installed Electron executable")
    parser.add_argument("--broker-directory", type=Path, default=ROOT / "dist/0.3.1")
    parser.add_argument("--results-directory", type=Path)
    args = parser.parse_args()
    artifacts = args.artifacts.resolve()
    broker_directory = args.broker_directory.resolve()
    results_directory = (args.results_directory or artifacts).resolve()
    results_directory.mkdir(parents=True, exist_ok=True)
    wheels = list(broker_directory.glob("codex_api_engine-*-py3-none-any.whl"))
    assert len(wheels) == 1, "expected_one_engine_wheel"
    work = ROOT / ".tmp" / ("clients040-" + uuid4().hex)
    work.mkdir()
    env = dict(os.environ, TEMP=str(ROOT / ".tmp"), TMP=str(ROOT / ".tmp"),
               npm_config_cache=str(ROOT / ".cache/npm"))
    env.pop("PYTHONPATH", None)
    python = work / "venv/Scripts/python.exe"
    run([sys.executable, "-m", "venv", str(work / "venv")], env)
    run([str(python), "-m", "pip", "install", "--no-index", "--no-deps",
         str(wheels[0]),
         str(artifacts / "python/cae_client-0.4.0-py3-none-any.whl")], env)
    run([shutil.which("npm.cmd") or "npm.cmd", "install", "--prefix", str(work / "node"),
         "--ignore-scripts", "--offline", "--no-audit", "--no-fund",
         str(artifacts / "nodejs/cae-client-0.4.0.tgz")], env)
    env["NODE_PATH"] = str(work / "node/node_modules")
    env["PSModulePath"] = str(artifacts / "powershell") + os.pathsep + env.get("PSModulePath", "")
    node = Path(shutil.which("node") or "node")
    powershell = Path(shutil.which("pwsh") or "pwsh")
    broker = broker_directory / "CAE-Broker.exe"
    dotnet = artifacts / "dotnet-client/Lab.Client.exe"
    admin = artifacts / "admin-client/Lab.Client.exe"
    cpp = artifacts / "CAE-Cpp-Client.exe"
    names = ["python", "dotnet", "cpp", "nodejs", "powershell"]
    if args.electron:
        names.append("electron")

    def enrollment(app: str, image: Path, admin: bool = False) -> dict[str, Any]:
        return {"app": app, "image": str(image.resolve()),
                "sha256": hashlib.sha256(image.read_bytes()).hexdigest(), "admin": admin}

    server = ThreadingHTTPServer(("127.0.0.1", 0), MockProvider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    runtime = work / "runtime.toml"
    runtime.write_text('schema_version = 1\n[[providers]]\nname = "lab"\nkind = "vllm"\n'
        f'endpoint = "http://127.0.0.1:{server.server_port}"\nauthenticated = false\n' + "".join(
            f'\n[[rules]]\nid = "{name}"\napp = "{name}"\nprovider = "lab"\n'
            'profile = "default"\noperations = ["models", "health", "diagnostics"]\n'
            for name in names), encoding="utf-8")
    pipe = "cae-lab-" + uuid4().hex
    record = enrollment("broker", broker)
    config = {"version": 1, "pipe": pipe, "runtime": str(runtime), "server": record,
        "clients": [enrollment("python", Path(process_peer(os.getpid()).image)),
                    enrollment("dotnet", dotnet), enrollment("cpp", cpp),
                    enrollment("nodejs", node), enrollment("powershell", powershell),
                    enrollment("lab-admin", admin, True)]}
    if args.electron:
        config["clients"].append(enrollment("electron", args.electron.resolve()))
    config_path = work / "broker.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    connection = {"pipe": pipe, "server_image": str(broker), "server_sha256": record["sha256"]}
    descriptor = work / "client.json"
    descriptor.write_text(json.dumps(connection), encoding="utf-8")
    env["CAE_CONNECTION_FILE"] = str(descriptor)
    monitor = BrokerClient(**connection)
    reports = {name: work / (name + ".json") for name in names}
    commands = {
        "python": [str(python), "-I", str(ROOT / "integration-lab/python-client/main.py")],
        "dotnet": [str(dotnet)], "cpp": [str(cpp)],
        "nodejs": [str(node), str(ROOT / "integration-lab/nodejs-client/main.js")],
        "powershell": [str(powershell), "-NoProfile", "-File", str(ROOT / "integration-lab/powershell-client/main.ps1")],
    }
    if args.electron:
        commands["electron"] = [str(args.electron.resolve()), str(ROOT / "integration-lab/electron-client/main.js")]
        env["CAE_LAB_DATA"] = str(work / "electron-state")
        env["CAE_CLIENT_PACKAGE"] = str(work / "node/node_modules/@cae/client")
        env.pop("ELECTRON_RUN_AS_NODE", None)
    processes: dict[str, subprocess.Popen[bytes]] = {}
    host: subprocess.Popen[bytes] | None = None

    def start() -> subprocess.Popen[bytes]:
        return subprocess.Popen([str(broker), "--config", str(config_path)], env=env,
                                creationflags=subprocess.CREATE_NO_WINDOW)

    try:
        host = start()
        for name, command in commands.items():
            processes[name] = subprocess.Popen([*command, str(reports[name])], env=env, cwd=work,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW)
        initial = wait_reports(reports)
        pid = initial["python"]["status"]["broker_pid"]
        # Unexpected termination of one application must not affect the other four.
        processes["cpp"].kill()
        processes["cpp"].wait(timeout=10)
        survivors = {name: path for name, path in reports.items() if name != "cpp"}
        surviving = wait_reports(survivors, expected_pid=pid, after=time.time())
        assert monitor.get_status()["broker_pid"] == pid
        run([str(admin), "stop"], env)
        host.wait(timeout=40)
        assert host.returncode == 0
        restarted_at = time.time()
        host = start()
        recovered = wait_reports(survivors, after=restarted_at)
        new_pid = recovered["python"]["status"]["broker_pid"]
        assert new_pid != pid
        assert all(processes[name].poll() is None for name in survivors)
        for name in survivors:
            Path(str(reports[name]) + ".stop").touch()
        for name in survivors:
            assert processes[name].wait(timeout=40) == 0
        assert monitor.get_status()["broker_pid"] == new_pid
        run([str(admin), "stop"], env)
        host.wait(timeout=40)
        assert host.returncode == 0
        assert MockProvider.calls >= 9
        assert MockProvider.posts == 0, "denied_generation_reached_provider"
        result = {"result": "passed", "provider": "mock loopback HTTP; no real model or cloud validation",
            "broker": str(broker), "broker_sha256": record["sha256"],
            "broker_version": initial["python"]["status"]["version"],
            "initial": initial, "survived_client_termination": surviving, "recovered": recovered,
            "mock_provider_calls": MockProvider.calls, "production_credentials_accessed": False,
            "clean_shutdown": True, "work": str(work)}
        output = results_directory / "CROSS-LANGUAGE-RESULTS.json"
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"result": "passed", "report": str(output), "broker_pid": pid,
                          "restarted_pid": new_pid, "languages": 5, "applications": len(names)}))
    finally:
        for process in processes.values():
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
        if host is not None and host.poll() is None:
            try:
                run([str(admin), "stop"], env)
                host.wait(timeout=40)
            except Exception:
                # Kill only the process tree started by this harness, never the operator broker.
                subprocess.run(["taskkill", "/PID", str(host.pid), "/T", "/F"], capture_output=True)
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
