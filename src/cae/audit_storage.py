"""Opt-in Windows JSONL retention. Private manifest owns every destructive action."""

import ctypes
import json
import os
import re
import stat
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

from .errors import AuditError, ConfigurationError
from .ipc_protocol import decode
from .pipe_transport import SECURITY_ATTRIBUTES, WinAPI, process_peer

MAX_RECORD = 4096
MAX_STATE = 65536


@dataclass(frozen=True)
class Retention:
    active_bytes: int = 1_048_576
    total_bytes: int = 8_388_608
    archive_count: int = 7
    archive_age_seconds: int = 2_592_000
    lock_timeout_ms: int = 2000

    def __post_init__(self) -> None:
        limits = {"active_bytes": (4096, 16_777_216), "total_bytes": (4096, 1_073_741_824),
                  "archive_count": (0, 64), "archive_age_seconds": (0, 315_360_000),
                  "lock_timeout_ms": (1, 10_000)}
        for key, (low, high) in limits.items():
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ConfigurationError()
        if self.total_bytes < self.active_bytes:
            raise ConfigurationError()


def safe_path(path: Path, *, directory: bool = False, missing: bool = False) -> os.stat_result | None:
    """Reject reparse components, alternate streams and hard-linked managed files."""
    if not path.is_absolute() or any(":" in part for part in path.parts[1:]):
        raise OSError()
    for parent in (*reversed(path.parents), path):
        try:
            info = parent.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise
        if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise OSError()
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing:
            return None
        raise
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise OSError()
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise OSError()
    return info


class JSONLStorage:
    """One bounded store, serialized across processes; no production migration."""

    def __init__(self, root: Path, retention: Retention,
                 validate: Callable[[bytes], None]) -> None:
        self.root = Path(os.path.abspath(root))
        self.retention, self.validate = retention, validate
        self.health = "unknown"
        self.failure = "none"
        self.recovery = "none"
        self.rejected = 0
        self._cache: tuple[int, int, int] | None = None

    def _path(self, name: str) -> Path:
        if name not in {"active.jsonl", "state.json", "state.new", "writer.lock"} and not re.fullmatch(
            r"archive-[0-9a-f]{32}-[0-9a-f]{32}\.jsonl", name
        ):
            raise OSError()
        path = self.root / name
        safe_path(path, missing=True)
        return path

    def _open(self, name: str, *, create: bool = False, exclusive: bool = False) -> BinaryIO:
        import msvcrt

        path = self._path(name)
        api = WinAPI()
        handle = api.open(str(path), 0xC0000000, 3, None,
                          1 if exclusive else 4 if create else 3, 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise OSError()
        try:
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
        except Exception:
            api.close(handle)
            raise
        try:
            stream = os.fdopen(descriptor, "r+b")
        except Exception:
            os.close(descriptor)
            raise
        try:
            info = os.fstat(stream.fileno())
            current = safe_path(path)
            if (info.st_nlink != 1 or current is None or info.st_ino != current.st_ino
                    or info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                raise OSError()
        except Exception:
            stream.close()
            raise
        return stream

    @staticmethod
    def _flush(stream: BinaryIO) -> None:
        stream.flush()
        os.fsync(stream.fileno())

    def _create_root(self) -> None:
        if safe_path(self.root, directory=True, missing=True) is not None:
            return
        safe_path(self.root.parent, directory=True, missing=True)
        self.root.parent.mkdir(parents=True, exist_ok=True)
        api = WinAPI()
        descriptor = ctypes.c_void_p()
        sid = process_peer(os.getpid()).sid
        if not api.security(f"D:P(A;OICI;GA;;;SY)(A;OICI;GA;;;{sid})", 1,
                            ctypes.byref(descriptor), None):
            raise OSError()
        try:
            attrs = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), descriptor, False)
            create = ctypes.WinDLL("kernel32", use_last_error=True).CreateDirectoryW
            create.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(SECURITY_ATTRIBUTES)]
            create.restype = ctypes.c_int
            if not create(str(self.root), ctypes.byref(attrs)) and ctypes.get_last_error() != 183:
                raise OSError()
        finally:
            api.free(descriptor)
        safe_path(self.root, directory=True)

    @contextmanager
    def _locked(self) -> Iterator[dict[str, Any]]:
        """All public operations use the same OS lock, including readers/recovery."""
        import msvcrt

        timed_out = False
        try:
            self._create_root()
            api = WinAPI()
            directory = api.open(str(self.root), 0, 3, None, 3, 0x02200000, None)
            if directory == ctypes.c_void_p(-1).value:
                raise OSError()
            try:
                safe_path(self.root, directory=True)
                with self._open("writer.lock", create=True) as lock:
                    deadline = time.monotonic() + self.retention.lock_timeout_ms / 1000
                    while True:
                        try:
                            lock.seek(0)
                            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                            break
                        except OSError:
                            if time.monotonic() >= deadline:
                                timed_out = True
                                raise
                            time.sleep(0.01)
                    try:
                        state = self._load()
                        self._recover(state)
                        yield state
                    finally:
                        lock.seek(0)
                        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                if not api.close(directory):
                    raise OSError()
            if self.health == "unknown":
                self.health = "ready"
        except Exception:
            self.health = "degraded"
            self.failure = "lock_timeout" if timed_out else "storage_unavailable"
            raise AuditError() from None

    def _validate_state(self, value: dict[str, Any]) -> None:
        if (set(value) != {"version", "owner", "active", "archives", "pending", "rotation_ns"}
                or type(value["version"]) is not int or value["version"] != 1
                or not isinstance(value["owner"], str)
                or not re.fullmatch("[0-9a-f]{32}", value["owner"])
                or type(value["rotation_ns"]) is not int or value["rotation_ns"] < 0
                or (value["active"] is not None and
                    (type(value["active"]) is not int or value["active"] <= 0))
                or not isinstance(value["archives"], list) or len(value["archives"]) > 65):
            raise OSError()
        names = set()
        for row in value["archives"]:
            if (not isinstance(row, dict) or set(row) != {"name", "file_id", "created_ns"}
                    or not isinstance(row["name"], str)
                    or not re.fullmatch("archive-" + value["owner"] + r"-[0-9a-f]{32}\.jsonl",
                                        row["name"])
                    or row["name"] in names or type(row["file_id"]) is not int
                    or row["file_id"] <= 0 or type(row["created_ns"]) is not int
                    or row["created_ns"] < 0):
                raise OSError()
            names.add(row["name"])
        pending = value["pending"]
        if pending is not None:
            if (not isinstance(pending, dict) or set(pending) != {"kind", "row"}
                    or pending["kind"] not in {"rotate", "delete"}):
                raise OSError()
            self._validate_state({**value, "archives": [pending["row"]], "pending": None})
            if (pending["kind"] == "delete" and pending["row"] not in value["archives"]
                    or pending["kind"] == "rotate" and
                    (pending["row"]["name"] in names or
                     pending["row"]["file_id"] != value["active"])):
                raise OSError()

    def _save(self, state: dict[str, Any]) -> None:
        self._validate_state(state)
        data = json.dumps(state, separators=(",", ":")).encode()
        if len(data) > MAX_STATE:
            raise OSError()
        with self._open("state.new", create=True) as stream:
            stream.seek(0)
            stream.truncate()
            if stream.write(data) != len(data):
                raise OSError()
            self._flush(stream)
        target, source = self._path("state.json"), self._path("state.new")
        if target.exists():
            replace = ctypes.WinDLL("kernel32", use_last_error=True).ReplaceFileW
            replace.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p,
                               ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]
            replace.restype = ctypes.c_int
            if not replace(str(target), str(source), None, 0, None, None):
                raise OSError()
        else:
            source.rename(target)  # On Windows, fails if destination exists.

    def _load(self) -> dict[str, Any]:
        if not self._path("state.json").exists():
            candidate = None
            if self._path("state.new").exists():
                try:
                    with self._open("state.new") as stream:
                        candidate = decode(stream.read(MAX_STATE + 1))
                    self._validate_state(candidate)
                except Exception:
                    candidate = None
            if candidate is not None:
                # ReplaceFile can fail after removing the old pathname. The fully
                # flushed replacement is sufficient to replay the pending intent.
                self._path("state.new").rename(self._path("state.json"))
                self.recovery = "manifest_recovered"
            else:
                # Incomplete first initialization is recoverable only before any
                # log exists. Never adopt a pre-existing active log or unknown file.
                with os.scandir(self.root) as entries:
                    for index, entry in enumerate(entries):
                        if index > 3 or entry.name not in {"writer.lock", "state.new"}:
                            raise OSError()
                self._save({"version": 1, "owner": uuid4().hex, "active": None,
                            "archives": [], "pending": None, "rotation_ns": 0})
        with self._open("state.json") as stream:
            state = decode(stream.read(MAX_STATE + 1))
        self._validate_state(state)
        return state

    def _owned(self, row: dict[str, Any], *, missing: bool = False) -> os.stat_result | None:
        info = safe_path(self._path(row["name"]), missing=missing)
        if info is not None and info.st_ino != row["file_id"]:
            raise OSError()
        return info

    def _recover(self, state: dict[str, Any]) -> None:
        pending = state["pending"]
        if pending is not None:
            row = pending["row"]
            info = self._owned(row, missing=True)
            if pending["kind"] == "delete":
                if info is not None:
                    self._path(row["name"]).unlink()
                state["archives"].remove(row)
            else:
                active = self._path("active.jsonl")
                if info is None:
                    self._owned({"name": "active.jsonl", "file_id": state["active"]})
                    active.rename(self._path(row["name"]))
                elif active.exists():
                    raise OSError()
                state["archives"].append(row)
                state["active"] = None
                state["rotation_ns"] = row["created_ns"]
            state["pending"] = None
            self._save(state)
            self.recovery = "transaction_recovered"
        if state["active"] is None:
            with self._open("active.jsonl", create=True) as stream:
                info = os.fstat(stream.fileno())
                if info.st_size:
                    raise OSError()
                self._flush(stream)
                state["active"] = info.st_ino
            self._save(state)
        self._owned({"name": "active.jsonl", "file_id": state["active"]})

    def _check_active(self, state: dict[str, Any]) -> int:
        with self._open("active.jsonl") as stream:
            info = os.fstat(stream.fileno())
            stamp = (info.st_ino, info.st_size, info.st_mtime_ns)
            if info.st_size > self.retention.active_bytes:
                raise OSError()
            if stamp != self._cache:
                good = 0
                while line := stream.readline(MAX_RECORD + 1):
                    if len(line) > MAX_RECORD:
                        raise OSError()
                    if not line.endswith(b"\n"):
                        # Only an unterminated final record is discardable. Full
                        # malformed records are corruption and require intervention.
                        stream.seek(good)
                        stream.truncate()
                        self._flush(stream)
                        self.recovery = "partial_tail_removed"
                        break
                    self.validate(line)
                    good = stream.tell()
                info = os.fstat(stream.fileno())
                self._cache = (info.st_ino, info.st_size, info.st_mtime_ns)
            return info.st_size

    def _prune(self, state: dict[str, Any], active_size: int, reserve: int = 0) -> None:
        rows = sorted(state["archives"], key=lambda r: (r["created_ns"], r["name"]))
        sizes = []
        for row in rows:
            info = self._owned(row)
            assert info is not None
            if info.st_size > self.retention.active_bytes:
                raise OSError()
            sizes.append(info.st_size)
        total = sum(sizes) + active_size + reserve
        now = time.time_ns()
        while rows:
            row = rows[0]
            expired = (self.retention.archive_age_seconds != 0 and
                       now - row["created_ns"] >= self.retention.archive_age_seconds * 10**9)
            if (not expired and len(rows) <= self.retention.archive_count
                    and total <= self.retention.total_bytes):
                break
            state["pending"] = {"kind": "delete", "row": row}
            self._save(state)
            self._recover(state)
            rows.pop(0)
            total -= sizes.pop(0)
        if total > self.retention.total_bytes:
            raise OSError()

    def append(self, data: bytes) -> None:
        try:
            if not data.endswith(b"\n") or len(data) > MAX_RECORD:
                raise AuditError()
            self.validate(data)
            with self._locked() as state:
                size = self._check_active(state)
                if size + len(data) > self.retention.active_bytes:
                    # Free archive capacity before introducing one new generation.
                    self._prune(state, size)
                    row = {"name": f"archive-{state['owner']}-{uuid4().hex}.jsonl",
                           "file_id": state["active"], "created_ns": max(time.time_ns(), state["rotation_ns"] + 1)}
                    if self._path(row["name"]).exists():
                        raise OSError()
                    state["pending"] = {"kind": "rotate", "row": row}
                    self._save(state)
                    self._recover(state)
                    size = 0
                self._prune(state, size, len(data))
                with self._open("active.jsonl") as stream:
                    stream.seek(0, 2)
                    if stream.write(data) != len(data):
                        raise OSError()
                    self._flush(stream)
                    info = os.fstat(stream.fileno())
                    self._cache = (info.st_ino, info.st_size, info.st_mtime_ns)
            self.health, self.failure = "ready", "none"
        except Exception:
            self.rejected += 1
            self.health = "degraded"
            raise AuditError() from None

    def records(self, capacity: int, *, archives: bool = False) -> list[bytes]:
        from collections import deque

        rows: deque[bytes] = deque(maxlen=capacity)
        with self._locked() as state:
            size = self._check_active(state)
            self._prune(state, size)
            entries = sorted(state["archives"], key=lambda r: (r["created_ns"], r["name"]))
            for row in (entries if archives else []) + [
                {"name": "active.jsonl", "file_id": state["active"]}
            ]:
                self._owned(row)
                with self._open(row["name"]) as stream:
                    while line := stream.readline(MAX_RECORD + 1):
                        if len(line) > MAX_RECORD or not line.endswith(b"\n"):
                            raise OSError()
                        self.validate(line)
                        rows.append(line)
        return list(rows)

    def status(self) -> dict[str, Any]:
        metrics: dict[str, Any] = {}
        try:
            with self._locked() as state:
                size = self._check_active(state)
                self._prune(state, size)
                sizes = [self._path(row["name"]).stat().st_size for row in state["archives"]]
                metrics = {"active_bytes": size, "archive_count": len(sizes),
                           "record_bytes": size + sum(sizes), "rotation_ns": state["rotation_ns"]}
        except AuditError:
            pass
        return {"mode": "managed_jsonl", "health": self.health, "failure": self.failure,
                "recovery": self.recovery, "rejected_events": self.rejected,
                "limits": asdict(self.retention), **metrics}
