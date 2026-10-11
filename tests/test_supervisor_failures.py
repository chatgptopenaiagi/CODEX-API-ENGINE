import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_broker_lifecycle import configuration

from cae.broker_control import control
from cae.pipe_transport import IPCError


@pytest.mark.parametrize("scenario", ["wrong_hash", "startup_timeout", "shutdown_timeout"])
def test_supervisor_failure_is_bounded_without_killing_processes(tmp_path, monkeypatch, scenario):
    config, settings, _ = configuration(tmp_path)
    settings = replace(settings, server=replace(settings.server, image=str(tmp_path / "CAE-Broker.exe")))
    monkeypatch.setattr("cae.broker_control.BrokerSettings.load", lambda _: settings)
    launched = []
    monkeypatch.setattr("cae.broker_control.subprocess", SimpleNamespace(
        Popen=lambda *args, **kwargs: launched.append((args, kwargs)),
        DEVNULL=subprocess.DEVNULL, CREATE_NO_WINDOW=subprocess.CREATE_NO_WINDOW))
    ticks = iter([0, 1, 41])
    monkeypatch.setattr("cae.broker_control.time", SimpleNamespace(
        monotonic=lambda: next(ticks), sleep=lambda _: None))
    monkeypatch.setattr("cae.broker_control.digest", lambda _: "0" * 64
                        if scenario == "wrong_hash" else settings.server.sha256)

    class Client:
        def __init__(self, *args):
            pass

        def stop(self):
            return {}

        def get_status(self):
            if scenario == "shutdown_timeout":
                return {"broker": "ready"}
            raise IPCError()

    monkeypatch.setattr("cae.broker_control.BrokerClient", Client)
    with pytest.raises(IPCError):
        control("stop" if scenario == "shutdown_timeout" else "start", config)
    if scenario == "startup_timeout":
        assert len(launched) == 1
        assert Path(launched[0][0][0][0]) == Path(settings.server.image)
        assert launched[0][1]["creationflags"] == subprocess.CREATE_NO_WINDOW
    else:
        assert not launched


@pytest.mark.parametrize("opened,error,result,raises", [
    (10, 0, 0, False), (10, 0, 258, True), (10, 0, 0xFFFFFFFF, True),
    (None, 87, 0, False), (None, 5, 0, True),
])
def test_shutdown_requires_process_exit_and_closes_handle(monkeypatch, opened, error, result, raises):
    from cae.broker_control import _wait_for_exit

    closed = []

    def open_process(rights, inherit, pid):
        assert rights == 0x00100000 and not inherit and pid == 123
        return opened

    def wait(handle, timeout):
        assert handle == 10 and timeout == 40_000
        return result

    kernel = SimpleNamespace(OpenProcess=open_process, WaitForSingleObject=wait,
                             CloseHandle=lambda handle: closed.append(handle))
    monkeypatch.setattr("cae.broker_control.ctypes.WinDLL", lambda *a, **k: kernel)
    monkeypatch.setattr("cae.broker_control.ctypes.get_last_error", lambda: error)
    if raises:
        with pytest.raises(IPCError):
            _wait_for_exit(123)
    else:
        _wait_for_exit(123)
    assert closed == ([10] if opened else [])


@pytest.mark.parametrize("pid", [0, -1, True, "123"])
def test_shutdown_rejects_invalid_process_identity(pid):
    from cae.broker_control import _wait_for_exit

    with pytest.raises(IPCError):
        _wait_for_exit(pid)
