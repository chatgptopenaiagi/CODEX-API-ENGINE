"""Explicit local supervisor. Never kills a process or alters system services."""

import ctypes
import subprocess
import time
from pathlib import Path
from typing import Any

from .broker_client import BrokerClient
from .ipc_protocol import BrokerSettings
from .pipe_transport import IPCError, digest


def _wait_for_exit(pid: int) -> None:
    """Wait for the authenticated broker process, not a transient pipe failure."""
    if type(pid) is not int or pid <= 0:
        raise IPCError()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.WaitForSingleObject.restype = ctypes.c_uint32
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only; no kill rights.
    if not handle:
        if ctypes.get_last_error() == 87:  # Process already exited (invalid PID).
            return
        raise IPCError()
    try:
        if kernel.WaitForSingleObject(handle, 40_000) != 0:
            raise IPCError()
    finally:
        kernel.CloseHandle(handle)


def control(action: str, config: Path) -> dict[str, Any]:
    settings = BrokerSettings.load(config)
    client = BrokerClient(settings.pipe, settings.server.image, settings.server.sha256)
    if action in {"stop", "restart"}:
        stopped = client.stop()
        _wait_for_exit(stopped.get("broker_pid", 0))
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
