"""Local Windows named pipes with bounded overlapped I/O and kernel peer identity."""

import ctypes as c
import hashlib
import os
import re
import time
from ctypes import wintypes as w
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any

from .errors import CAEError

MAX_MESSAGE = 65_536


class IPCError(CAEError):
    code = "broker_unavailable"


class ProtocolError(CAEError):
    code = "invalid_protocol"


class OVERLAPPED(c.Structure):
    _fields_ = [("internal", c.c_size_t), ("high", c.c_size_t),
                ("offset", w.DWORD), ("offset_high", w.DWORD), ("event", w.HANDLE)]


class SECURITY_ATTRIBUTES(c.Structure):
    _fields_ = [("length", w.DWORD), ("descriptor", w.LPVOID), ("inherit", w.BOOL)]


def _bind(dll: Any, name: str, result: Any, args: list[Any]) -> Any:
    fn = getattr(dll, name)
    fn.restype, fn.argtypes = result, args
    return fn


class WinAPI:
    def __init__(self) -> None:
        if os.name != "nt":
            raise IPCError()
        kernel = c.WinDLL("kernel32", use_last_error=True)
        advapi = c.WinDLL("advapi32", use_last_error=True)
        ptr = c.POINTER
        self.close = _bind(kernel, "CloseHandle", w.BOOL, [w.HANDLE])
        self.free = _bind(kernel, "LocalFree", w.HANDLE, [w.HANDLE])
        self.create = _bind(kernel, "CreateNamedPipeW", w.HANDLE,
                            [w.LPCWSTR, w.DWORD, w.DWORD, w.DWORD, w.DWORD, w.DWORD,
                             w.DWORD, ptr(SECURITY_ATTRIBUTES)])
        self.open = _bind(kernel, "CreateFileW", w.HANDLE,
                          [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE])
        self.connect = _bind(kernel, "ConnectNamedPipe", w.BOOL, [w.HANDLE, ptr(OVERLAPPED)])
        self.disconnect = _bind(kernel, "DisconnectNamedPipe", w.BOOL, [w.HANDLE])
        self.read = _bind(kernel, "ReadFile", w.BOOL,
                          [w.HANDLE, w.LPVOID, w.DWORD, ptr(w.DWORD), ptr(OVERLAPPED)])
        self.write = _bind(kernel, "WriteFile", w.BOOL,
                           [w.HANDLE, w.LPCVOID, w.DWORD, ptr(w.DWORD), ptr(OVERLAPPED)])
        self.event = _bind(kernel, "CreateEventW", w.HANDLE,
                           [w.LPVOID, w.BOOL, w.BOOL, w.LPCWSTR])
        self.wait = _bind(kernel, "WaitForSingleObject", w.DWORD, [w.HANDLE, w.DWORD])
        self.cancel = _bind(kernel, "CancelIoEx", w.BOOL, [w.HANDLE, ptr(OVERLAPPED)])
        self.result = _bind(kernel, "GetOverlappedResult", w.BOOL,
                            [w.HANDLE, ptr(OVERLAPPED), ptr(w.DWORD), w.BOOL])
        self.client_pid = _bind(kernel, "GetNamedPipeClientProcessId", w.BOOL,
                                [w.HANDLE, ptr(w.ULONG)])
        self.server_pid = _bind(kernel, "GetNamedPipeServerProcessId", w.BOOL,
                                [w.HANDLE, ptr(w.ULONG)])
        self.process = _bind(kernel, "OpenProcess", w.HANDLE, [w.DWORD, w.BOOL, w.DWORD])
        self.image = _bind(kernel, "QueryFullProcessImageNameW", w.BOOL,
                           [w.HANDLE, w.DWORD, w.LPWSTR, ptr(w.DWORD)])
        self.token = _bind(advapi, "OpenProcessToken", w.BOOL,
                           [w.HANDLE, w.DWORD, ptr(w.HANDLE)])
        self.token_info = _bind(advapi, "GetTokenInformation", w.BOOL,
                                [w.HANDLE, c.c_int, w.LPVOID, w.DWORD, ptr(w.DWORD)])
        self.sid_string = _bind(advapi, "ConvertSidToStringSidW", w.BOOL,
                                [w.LPVOID, ptr(w.LPWSTR)])
        self.security = _bind(advapi, "ConvertStringSecurityDescriptorToSecurityDescriptorW",
                              w.BOOL, [w.LPCWSTR, w.DWORD, ptr(w.LPVOID), w.LPVOID])


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@dataclass(frozen=True)
class Peer:
    pid: int
    sid: str
    image: str
    sha256: str


def process_peer(pid: int) -> Peer:
    api = WinAPI()
    process = api.process(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    token = w.HANDLE()
    if not process:
        raise IPCError()
    try:
        path = c.create_unicode_buffer(32768)
        size = w.DWORD(len(path))
        if not api.image(process, 0, path, c.byref(size)):
            raise IPCError()
        if not api.token(process, 8, c.byref(token)):
            raise IPCError()
        needed = w.DWORD()
        api.token_info(token, 1, None, 0, c.byref(needed))
        if not 0 < needed.value < 65536:
            raise IPCError()
        buffer = c.create_string_buffer(needed.value)
        if not api.token_info(token, 1, buffer, len(buffer), c.byref(needed)):
            raise IPCError()
        sid_ptr = c.cast(buffer, c.POINTER(w.LPVOID))[0]
        string = w.LPWSTR()
        if not api.sid_string(sid_ptr, c.byref(string)):
            raise IPCError()
        try:
            sid = string.value or ""
        finally:
            api.free(c.cast(string, w.HANDLE))
        return Peer(pid, sid, str(Path(path.value).resolve()), digest(Path(path.value)))
    finally:
        if token:
            api.close(token)
        api.close(process)


def pipe_path(name: str) -> str:
    if not re.fullmatch(r"cae-[a-z0-9-]{1,64}", name):
        raise ProtocolError()
    return "\\\\.\\pipe\\" + name


class Pipe:
    def __init__(self, handle: int) -> None:
        self.handle = handle
        self.api = WinAPI()

    @classmethod
    def listener(cls, name: str, sid: str, *, first: bool = False) -> Pipe:
        api = WinAPI()
        descriptor = w.LPVOID()
        # Protected DACL: this account and SYSTEM only; no inherited/world/network ACE.
        sddl = f"D:P(A;;GA;;;SY)(A;;GA;;;{sid})"
        if not api.security(sddl, 1, c.byref(descriptor), None):
            raise IPCError()
        try:
            attrs = SECURITY_ATTRIBUTES(c.sizeof(SECURITY_ATTRIBUTES), descriptor, False)
            handle = api.create(pipe_path(name), 3 | 0x40000000 | (0x80000 if first else 0),
                                8, 16, MAX_MESSAGE + 4, MAX_MESSAGE + 4, 1000,
                                c.byref(attrs))  # PIPE_REJECT_REMOTE_CLIENTS, byte stream
        finally:
            api.free(descriptor)
        if handle == c.c_void_p(-1).value:
            raise IPCError()
        return cls(handle)

    @classmethod
    def dial(cls, name: str, timeout: float = 3) -> Pipe:
        api = WinAPI()
        deadline = time.monotonic() + timeout
        while True:
            handle = api.open(pipe_path(name), 0xC0000000, 0, None, 3,
                              0x40000000 | 0x100000 | 0x10000, None)
            # OVERLAPPED + SECURITY_SQOS_PRESENT + SECURITY_IDENTIFICATION
            if handle != c.c_void_p(-1).value:
                return cls(handle)
            if c.get_last_error() not in {2, 231} or time.monotonic() >= deadline:
                raise IPCError()
            time.sleep(0.025)

    def peer(self, *, server: bool = False) -> Peer:
        pid = w.ULONG()
        fn = self.api.server_pid if server else self.api.client_pid
        if not fn(self.handle, c.byref(pid)):
            raise IPCError()
        return process_peer(pid.value)

    def _io(self, mode: str, buffer: Any, size: int, deadline: float,
            stop: Event | None = None) -> int:
        if time.monotonic() >= deadline:
            raise IPCError()
        event = self.api.event(None, True, False, None)
        if not event:
            raise IPCError()
        overlap = OVERLAPPED(event=event)
        count = w.DWORD()
        pending = False
        try:
            if mode == "connect":
                ok = self.api.connect(self.handle, c.byref(overlap))
            else:
                fn = self.api.read if mode == "read" else self.api.write
                ok = fn(self.handle, buffer, size, c.byref(count), c.byref(overlap))
            if not ok:
                error = c.get_last_error()
                if mode == "connect" and error == 535:
                    return 0
                if error != 997:
                    raise IPCError()
                pending = True
                while self.api.wait(event, 25) == 258:
                    if time.monotonic() >= deadline or (stop is not None and stop.is_set()):
                        raise IPCError()
                if not self.api.result(self.handle, c.byref(overlap), c.byref(count), False):
                    raise IPCError()
                pending = False
            return count.value
        finally:
            if pending:
                self.api.cancel(self.handle, c.byref(overlap))
                self.api.result(self.handle, c.byref(overlap), c.byref(count), True)
            self.api.close(event)

    def accept(self, stop: Event) -> None:
        self._io("connect", None, 0, float("inf"), stop)

    def read_exact(self, size: int, deadline: float) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            buffer = c.create_string_buffer(size - len(chunks))
            count = self._io("read", buffer, len(buffer), deadline)
            if not count:
                raise IPCError()
            chunks.extend(buffer.raw[:count])
        return bytes(chunks)

    def receive(self, timeout: float = 3) -> bytes:
        deadline = time.monotonic() + timeout
        size = int.from_bytes(self.read_exact(4, deadline), "little")
        if not 0 < size <= MAX_MESSAGE:
            raise ProtocolError()
        return self.read_exact(size, deadline)

    def send(self, data: bytes, timeout: float = 3) -> None:
        if not 0 < len(data) <= MAX_MESSAGE:
            raise ProtocolError()
        raw = len(data).to_bytes(4, "little") + data
        deadline = time.monotonic() + timeout
        offset = 0
        while offset < len(raw):
            buffer = c.create_string_buffer(raw[offset:])
            count = self._io("write", buffer, len(raw) - offset, deadline)
            if not count:
                raise IPCError()
            offset += count

    def disconnect(self) -> None:
        self.api.disconnect(self.handle)

    def close(self) -> None:
        if self.handle:
            self.api.close(self.handle)
            self.handle = 0
