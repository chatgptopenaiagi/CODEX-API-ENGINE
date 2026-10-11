"""Explicit local supervisor. Never kills a process or alters system services."""

import subprocess
import time
from pathlib import Path
from typing import Any

from .broker_client import BrokerClient
from .ipc_protocol import BrokerSettings
from .pipe_transport import IPCError, digest


def control(action: str, config: Path) -> dict[str, Any]:
    settings = BrokerSettings.load(config)
    client = BrokerClient(settings.pipe, settings.server.image, settings.server.sha256)
    if action in {"stop", "restart"}:
        client.stop()
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            try:
                client.get_status()
            except IPCError:
                break
            time.sleep(0.1)
        else:
            raise IPCError()
        if action == "stop":
            return {"broker": "stopped"}
    if action in {"start", "restart"}:
        try:
            return client.get_status()
        except IPCError:
            pass
        executable = Path(settings.server.image)
        if digest(executable) != settings.server.sha256:
            raise IPCError()
        # Frozen broker only; source development starts python -m cae.broker_service explicitly.
        if executable.name.lower() != "cae-broker.exe":
            raise IPCError()
        subprocess.Popen([str(executable), "--config", str(config.resolve())],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                return client.get_status()
            except IPCError:
                time.sleep(0.1)
        raise IPCError()
    if action == "status":
        return client.get_status()
    if action == "health":
        return client.health()
    if action == "diagnostics":
        return client.diagnostics()
    raise IPCError()
