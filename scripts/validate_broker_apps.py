"""Run from an installed wheel with -I. Real EXEs, real IPC; live probe is opt-in."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import cae
from cae import BrokerClient, CAEError
from cae.pipe_transport import digest, process_peer


def wait_report(path, predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = json.loads(path.read_text())
            if predicate(value):
                return value
        except (OSError, ValueError):
            pass
        time.sleep(0.1)
    raise AssertionError("Client report timed out")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    assert "site-packages" in str(Path(cae.__file__).resolve())
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    artifacts = args.artifacts.resolve()
    runtime = work / "runtime.toml"
    runtime.write_text('schema_version = 1\n[[providers]]\nname = "openai"\nkind = "openai"\n'
                       + "\n".join(
                           f'[[rules]]\nid = "{app}-read"\napp = "{app}"\n'
                           'provider = "openai"\nprofile = "default"\n'
                           'operations = ["diagnostics", "health", "models", "usage"]\n'
                           for app in ("console-client", "desktop-client", "broker-admin")))
    server = artifacts / "CAE-Broker.exe"
    peer = process_peer(os.getpid())
    identities = [{"app": "broker-admin", "image": peer.image, "sha256": peer.sha256,
                   "admin": True}]
    for name, executable in (("console-client", "CAE-Console-Client.exe"),
                             ("desktop-client", "CAE-Desktop-Client.exe")):
        path = artifacts / executable
        identities.append({"app": name, "image": str(path), "sha256": digest(path)})
    connection = {"pipe": "cae-validation-" + str(os.getpid()), "server_image": str(server),
                  "server_sha256": digest(server)}
    config = work / "broker.json"
    config.write_text(json.dumps({"version": 1, "pipe": connection["pipe"],
                                  "runtime": str(runtime), "server": {
                                      "app": "broker", "image": str(server),
                                      "sha256": connection["server_sha256"]},
                                  "clients": identities}))
    client_config = work / "client.json"
    client_config.write_text(json.dumps(connection))
    client = BrokerClient(**connection)

    def command(action):
        process = subprocess.run([sys.executable, "-I", "-m", "cae", "broker", action,
                                  "--config", str(config)], cwd=work, capture_output=True,
                                 timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        assert process.returncode == 0, f"Broker lifecycle failed: {action}"
        return json.loads(process.stdout)

    processes = []
    outcomes = {"version": cae.__version__, "installed_wheel": True}
    try:
        first = command("start")
        assert first["broker_mode"] == "named_pipe"
        assert command("status")["broker_pid"] == first["broker_pid"]
        assert command("health")["broker"] == "ready"
        assert command("diagnostics")["broker_mode"] == "named_pipe"
        for letter, executable in (("a", "CAE-Console-Client.exe"),
                                   ("b", "CAE-Desktop-Client.exe")):
            processes.append(subprocess.Popen(
                [str(artifacts / executable), "--connection", str(client_config),
                 "--verify-denial",
                 "--report", str(work / f"{letter}.json"),
                 "--stop-file", str(work / f"{letter}.stop")], cwd=work,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW))
        a = wait_report(work / "a.json", lambda row: row["cycles"] >= 2)
        b = wait_report(work / "b.json", lambda row: row["cycles"] >= 2)
        assert a["broker_pid"] == b["broker_pid"] == first["broker_pid"]
        assert a["client_pid"] != b["client_pid"] != first["broker_pid"]
        assert a["authenticated_app"] == "console-client"
        assert b["authenticated_app"] == "desktop-client"
        assert a["admin_denied"] and b["admin_denied"]
        for operation, kwargs in (("export", {}), ("models", {"app": "broker-admin"}),
                                  ("chat", {"model": "forbidden", "text": "denied"})):
            try:
                client.request(operation, **kwargs)
            except CAEError as exc:
                assert exc.code in {"access_denied", "invalid_protocol"}
            else:
                raise AssertionError("Unauthorized operation accepted")
        # Abruptly terminate only our Application A process tree, including onefile child.
        killed = subprocess.run(["taskkill", "/PID", str(processes[0].pid), "/T", "/F"],
                                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        assert killed.returncode == 0
        processes[0].wait(timeout=10)
        later = wait_report(work / "b.json", lambda row: row["cycles"] >= b["cycles"] + 3)
        assert later["broker_pid"] == first["broker_pid"]
        assert later["admin_denied"]
        diagnostics = client.diagnostics()
        assert later["credential"] == diagnostics["credential"]
        outcomes.update(same_broker_pid=first["broker_pid"], console=a, desktop_before=b,
                        desktop_after_console_termination=later,
                        unauthorized_operations_denied=True, broker_survived=True)
        if args.live:
            result = client.health(probe=True)  # Exactly one models GET; no paid generation.
            assert result["authentication"] == "valid" and result["api"] == "available"
            outcomes["openai_probe"] = {key: result[key] for key in (
                "authentication", "api", "credential", "broker", "broker_mode")}
        (work / "b.stop").touch()
        assert processes[1].wait(timeout=10) == 0
        assert command("stop")["broker"] == "stopped"
        second = command("start")
        assert second["broker_pid"] != first["broker_pid"]
        third = command("restart")
        assert third["broker_pid"] != second["broker_pid"]
        # Simulate a broker crash, then prove explicit startup recovery (no stale PID trust).
        killed = subprocess.run(["taskkill", "/PID", str(third["broker_pid"]), "/T", "/F"],
                                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        assert killed.returncode == 0
        try:
            client.get_status()
        except CAEError:
            pass
        else:
            raise AssertionError("Crashed broker still responded")
        recovered = command("start")
        assert recovered["broker_pid"] != third["broker_pid"]
        assert command("stop")["broker"] == "stopped"
        outcomes.update(clean_shutdown=True, restart=True, crash_recovery=True,
                        production_credentials_written=False, result="SUCCESS")
        (work / "results.json").write_text(json.dumps(outcomes, indent=2))
        print(json.dumps(outcomes, indent=2))
    finally:
        for letter in ("a", "b"):
            (work / f"{letter}.stop").touch()
        for process in processes:
            if process.poll() is None:
                process.wait(timeout=40)
        try:
            client.stop()
        except CAEError:
            pass


if __name__ == "__main__":
    main()
