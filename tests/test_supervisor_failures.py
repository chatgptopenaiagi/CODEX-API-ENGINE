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
