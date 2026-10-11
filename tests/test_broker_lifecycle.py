import ctypes as c
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes as w
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from cae import BrokerClient
from cae.broker_control import control
from cae.broker_service import BrokerServer
from cae.cli import main as cli_main
from cae.errors import AccessDenied
from cae.ipc_protocol import BrokerSettings
from cae.pipe_transport import IPCError, Pipe, process_peer


def configuration(tmp_path):
    peer = process_peer(os.getpid())
    runtime = tmp_path / "runtime.toml"
    runtime.write_text('schema_version = 1\n[[providers]]\nname = "openai"\n'
                       'kind = "ollama"\nauthenticated = false\n[[rules]]\n'
                       'id = "offline"\napp = "test-admin"\nprovider = "openai"\n'
                       'profile = "default"\noperations = ["diagnostics"]\n')
    enrollment = {"app": "test-admin", "image": peer.image, "sha256": peer.sha256,
                  "admin": True}
    config = tmp_path / "broker.json"
    config.write_text(json.dumps({"version": 1, "pipe": "cae-process-" + uuid4().hex,
                                  "runtime": str(runtime), "server": enrollment,
                                  "clients": [enrollment]}))
    settings = BrokerSettings.load(config)
    return config, settings, BrokerClient(settings.pipe, peer.image, peer.sha256)


def launch(config, client):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    process = subprocess.Popen([sys.executable, "-m", "cae.broker_service", "--config",
                                str(config)], env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            status = client.get_status()
            assert status["broker_pid"] != os.getpid()
            return process, status
        except IPCError:
            pass
    process.terminate()
    process.wait(5)
    raise AssertionError("Broker subprocess startup failed")


def test_separate_process_lifecycle_and_cli(tmp_path, capsys):
    config, settings, client = configuration(tmp_path)
    process, first = launch(config, client)
    try:
        assert control("status", config)["broker_pid"] == first["broker_pid"]
        assert control("start", config)["broker_pid"] == first["broker_pid"]
        assert control("health", config)["credential"] == "not_required"
        assert control("diagnostics", config)["broker_mode"] == "named_pipe"
        assert cli_main(["broker", "status", "--config", str(config)]) == 0
        assert "named_pipe" in capsys.readouterr().out
        assert cli_main(["broker", "status"]) == 1
        assert "invalid_configuration" in capsys.readouterr().out
        assert control("stop", config) == {"broker": "stopped"}
        assert process.wait(10) == 0
        with pytest.raises(IPCError):
            client.get_status()
        process, second = launch(config, client)
        assert second["broker_pid"] != first["broker_pid"]
        # Kill the actual Python child (a venv redirector may be the Popen parent).
        subprocess.run(["taskkill", "/PID", str(second["broker_pid"]), "/T", "/F"],
                       capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        process.wait(10)
        with pytest.raises(IPCError):
            client.get_status()
        process, third = launch(config, client)
        assert third["broker_pid"] != second["broker_pid"]
        assert client.diagnostics()["credential"] == "not_required"
    finally:
        if process.poll() is None:
            client.stop()
            assert process.wait(10) == 0


def test_untrusted_server_and_control_refuse_interpreter_start(tmp_path):
    config, settings, _ = configuration(tmp_path)
    with pytest.raises(IPCError):
        control("start", config)
    with pytest.raises(IPCError):
        control("invalid", config)
    with pytest.raises(AccessDenied):
        BrokerServer(replace(settings, server=replace(settings.server, sha256="0" * 64)), None)


def test_actual_pipe_dacl_is_protected_and_account_scoped():
    peer = process_peer(os.getpid())
    pipe = Pipe.listener("cae-acl-" + uuid4().hex, peer.sid, first=True)
    advapi = c.WinDLL("advapi32", use_last_error=True)
    get = advapi.GetSecurityInfo
    get.argtypes = [w.HANDLE, c.c_int, w.DWORD, w.LPVOID, w.LPVOID,
                   w.LPVOID, w.LPVOID, c.POINTER(w.LPVOID)]
    get.restype = w.DWORD
    convert = advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW
    convert.argtypes = [w.LPVOID, w.DWORD, w.DWORD, c.POINTER(w.LPWSTR), w.LPVOID]
    convert.restype = w.BOOL
    descriptor = w.LPVOID()
    dacl = w.LPVOID()
    text = w.LPWSTR()
    try:
        assert get(pipe.handle, 1, 4, None, None, c.byref(dacl), None, c.byref(descriptor)) == 0
        assert convert(descriptor, 1, 4, c.byref(text), None)
        sddl = text.value
        assert sddl.startswith("D:P")
        # SDDL aliases built-in users (e.g. RID 500 -> LA); verify the binary ACE SIDs.
        get_ace = advapi.GetAce
        get_ace.argtypes = [w.LPVOID, w.DWORD, c.POINTER(w.LPVOID)]
        get_ace.restype = w.BOOL
        count = c.cast(dacl, c.POINTER(c.c_ushort))[2]
        assert count == 2
        trustees = set()
        for index in range(count):
            ace = w.LPVOID()
            assert get_ace(dacl, index, c.byref(ace))
            assert c.cast(ace, c.POINTER(c.c_byte))[0] == 0  # ACCESS_ALLOWED_ACE
            sid = w.LPWSTR()
            assert pipe.api.sid_string(ace.value + 8, c.byref(sid))
            trustees.add(sid.value)
            pipe.api.free(c.cast(sid, w.HANDLE))
        assert trustees == {peer.sid, "S-1-5-18"}
    finally:
        if text:
            pipe.api.free(c.cast(text, w.HANDLE))
        if descriptor:
            pipe.api.free(descriptor)
        pipe.close()
