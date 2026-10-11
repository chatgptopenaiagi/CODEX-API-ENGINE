"""Windows Credential Manager backend and administrator-only credential lifecycle."""

import ctypes
import hmac
import os
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path
from threading import RLock
from typing import Protocol

from .audit import AuditLog
from .errors import CredentialError, CredentialExists, CredentialMissing
from .security import identifier, validate_key


class CredentialStore(Protocol):
    """Trusted infrastructure interface, deliberately outside the application SDK."""

    def read(self, profile: str) -> str: ...
    def write(self, profile: str, secret: str) -> None: ...
    def delete(self, profile: str) -> None: ...
    def exists(self, profile: str) -> bool: ...


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(wintypes.BYTE)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialStore:
    """OS user scoped generic credentials; no plaintext fallback or environment lookup."""

    def __init__(self, provider: str = "openai") -> None:
        self._provider = identifier(provider)
        if os.name != "nt":
            raise CredentialError()
        self._dll = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        pointer = ctypes.POINTER(_Credential)
        self._dll.CredWriteW.argtypes = [pointer, wintypes.DWORD]
        self._dll.CredWriteW.restype = wintypes.BOOL
        self._dll.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(pointer),
        ]
        self._dll.CredReadW.restype = wintypes.BOOL
        self._dll.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self._dll.CredDeleteW.restype = wintypes.BOOL
        self._dll.CredFree.argtypes = [ctypes.c_void_p]
        self._dll.CredFree.restype = None

    def _target(self, profile: str) -> str:
        return "CAE/" + self._provider + "/" + identifier(profile)

    def read(self, profile: str) -> str:
        ptr = ctypes.POINTER(_Credential)()
        if not self._dll.CredReadW(self._target(profile), 1, 0, ctypes.byref(ptr)):
            if ctypes.get_last_error() == 1168:
                raise CredentialMissing()
            raise CredentialError()
        failed = False
        secret = ""
        try:
            secret = ctypes.string_at(
                ptr.contents.CredentialBlob, ptr.contents.CredentialBlobSize
            ).decode("utf-8")
        except Exception:
            failed = True
        finally:
            if ptr.contents.CredentialBlob and ptr.contents.CredentialBlobSize:
                ctypes.memset(ptr.contents.CredentialBlob, 0, ptr.contents.CredentialBlobSize)
            self._dll.CredFree(ptr)
        if failed:
            raise CredentialError()
        return secret

    def write(self, profile: str, secret: str) -> None:
        target = self._target(profile)
        validate_key(secret, self._provider)
        data = bytearray(secret, "utf-8")
        buffer = (wintypes.BYTE * len(data)).from_buffer(data)
        credential = _Credential()
        credential.Type = 1  # CRED_TYPE_GENERIC
        credential.TargetName = target
        credential.CredentialBlobSize = len(data)
        credential.CredentialBlob = buffer
        credential.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE: current user, this machine
        credential.UserName = "CAE"
        try:
            ok = self._dll.CredWriteW(ctypes.byref(credential), 0)
        finally:
            ctypes.memset(buffer, 0, len(data))
        if not ok:
            raise CredentialError()

    def exists(self, profile: str) -> bool:
        try:
            self.read(profile)
        except CredentialMissing:
            return False
        return True

    def delete(self, profile: str) -> None:
        if not self._dll.CredDeleteW(self._target(profile), 1, 0):
            if ctypes.get_last_error() != 1168:
                raise CredentialError()


class CredentialManager:
    """Human/admin API. No export or raw-key retrieval method."""

    def __init__(
        self,
        store: CredentialStore | None = None,
        *,
        provider: str = "openai",
        audit: AuditLog | None = None,
    ) -> None:
        self._provider = identifier(provider)
        self._audit_log = audit if audit is not None else AuditLog()
        self._store = store if store is not None else WindowsCredentialStore(provider)
        self._lock = RLock()

    def exists(self, profile: str = "default") -> bool:
        self._audit_log.emit("credential_checked", provider=self._provider, profile=profile)
        return self._store.exists(identifier(profile))

    def add(self, secret: str, profile: str = "default") -> None:
        validate_key(secret, self._provider)
        with self._lock:
            if self.exists(profile):
                raise CredentialExists()
            self._change(profile, "credential_added", lambda: self._write(profile, secret))

    def replace(self, secret: str, profile: str = "default") -> None:
        validate_key(secret, self._provider)
        with self._lock:
            if not self.exists(profile):
                raise CredentialMissing()
            self._change(profile, "credential_replaced", lambda: self._write(profile, secret))

    def rotate(self, secret: str, profile: str = "default") -> None:
        """Replace locally. Provider-side creation/revocation remains a human operation."""
        self.replace(secret, profile)

    def remove(self, profile: str = "default") -> None:
        with self._lock:
            self._change(
                identifier(profile), "credential_removed", lambda: self._store.delete(profile)
            )

    def _write(self, profile: str, secret: str) -> None:
        self._store.write(profile, secret)
        self._verify(profile, secret)

    def _change(self, profile: str, event: str, action: Callable[[], None]) -> None:
        self._audit_log.emit(
            "credential_change_requested", provider=self._provider, profile=profile
        )
        failed = False
        try:
            action()
        except Exception:
            failed = True
        if failed:
            self._audit_log.emit("credential_failed", provider=self._provider, profile=profile)
            raise CredentialError()
        self._audit_log.emit(event, provider=self._provider, profile=profile)

    def _verify(self, profile: str, secret: str) -> None:
        if not hmac.compare_digest(self._store.read(profile), secret):
            raise CredentialError()

    def import_file(self, path: Path, profile: str = "default", *, replace: bool = False) -> None:
        """Read once into memory; never delete, echo, copy or persist the source."""
        secret = ""
        failed = False
        try:
            if path.is_symlink() or path.stat().st_size > 4096:
                raise CredentialError()
            secret = path.read_text(encoding="utf-8-sig").strip()
            validate_key(secret, self._provider)
        except Exception:
            failed = True
        if failed:
            raise CredentialError()
        try:
            if replace:
                self.replace(secret, profile)
            else:
                self.add(secret, profile)
        finally:
            secret = ""
