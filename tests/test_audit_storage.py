"""Real Windows files, isolated roots; synthetic failure injection only."""

import ctypes
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from test_access_platform import runtime

from cae.audit import AuditLog, request_scope
from cae.audit_storage import JSONLStorage, Retention, safe_path
from cae.config import audit_retention, load_runtime, parse_config
from cae.errors import AuditError, ConfigurationError
from cae.pipe_transport import WinAPI


def storage(tmp_path, **limits):
    return JSONLStorage(tmp_path / "managed", Retention(active_bytes=4096, **limits),
                        lambda data: json.loads(data))


def record(index=0, size=1024):
    data = json.dumps({"n": index}).encode()
    return data + b" " * (size - len(data) - 1) + b"\n"


def state(sink):
    return json.loads((sink.root / "state.json").read_bytes())


def test_boundaries_rotation_and_legacy_reader(tmp_path):
    sink = storage(tmp_path, total_bytes=12288, archive_count=2)
    for index in range(16):
        sink.append(record(index))
        status = sink.status()
        assert status["record_bytes"] <= 12288 and status["archive_count"] <= 2
    assert [json.loads(row)["n"] for row in sink.records(100, archives=True)] == list(range(4, 16))
    assert [json.loads(row)["n"] for row in sink.records(100)] == list(range(12, 16))
    assert len((sink.root / "active.jsonl").read_text().splitlines()) == 4
    assert sink.status()["health"] == "ready"


@pytest.mark.parametrize("count,total,expected", [(0,8192,4), (7,4096,4), (1,8192,8)])
def test_independent_limits(tmp_path, count, total, expected):
    sink = storage(tmp_path, total_bytes=total, archive_count=count)
    for index in range(12):
        sink.append(record(index))
    assert len(sink.records(100, archives=True)) == expected


def test_age_boundary_unknown_files_and_idempotence(tmp_path, monkeypatch):
    sink = storage(tmp_path, archive_age_seconds=10)
    for index in range(5):
        sink.append(record(index))
    metadata = state(sink)
    created = metadata["archives"][0]["created_ns"]
    unknown = sink.root / "archive-not-owned.jsonl"
    unknown.write_bytes(b"unrelated")
    monkeypatch.setattr(time, "time_ns", lambda: created + 10 * 10**9 - 1)
    assert sink.status()["archive_count"] == 1
    monkeypatch.setattr(time, "time_ns", lambda: created + 10 * 10**9)
    assert sink.status()["archive_count"] == 0
    assert sink.status()["archive_count"] == 0
    assert unknown.read_bytes() == b"unrelated"


def test_disabled_age(tmp_path, monkeypatch):
    sink = storage(tmp_path, archive_age_seconds=0)
    for index in range(5):
        sink.append(record(index))
    monkeypatch.setattr(time, "time_ns", lambda: 2**62)
    assert sink.status()["archive_count"] == 1


@pytest.mark.parametrize("limits", [{"active_bytes":4095}, {"total_bytes":4095},
    {"archive_count":-1}, {"archive_count":65}, {"archive_count":True},
    {"archive_age_seconds":float("nan")}, {"lock_timeout_ms":0},
    {"active_bytes":8192,"total_bytes":4096}, {"total_bytes":2**40}])
def test_invalid_limits(limits):
    with pytest.raises(ConfigurationError):
        Retention(**limits)


def test_config_and_sdk_compatibility(tmp_path):
    text = 'schema_version=1\n[[providers]]\nname="local"\nkind="ollama"\nauthenticated=false\n'
    assert audit_retention(text) is None
    for extra in ['[audit]\nmode="wrong"', '[audit]\nmode="managed"\nunknown=1',
                  '[audit]\nmode="managed"\narchive_count=true', '[audit]\nactive_bytes=4096']:
        with pytest.raises(ConfigurationError):
            parse_config(text + extra)
    path = tmp_path / "runtime.toml"
    path.write_text(text + '[audit]\nmode="managed"\nactive_bytes=4096\n')
    access = load_runtime(path)
    try:
        assert access.audit_log.storage_status()["mode"] == "managed_jsonl"
        assert access.audit_log.events()[0]["event"] == "configuration_loaded"
        assert not (tmp_path / ".cae" / "audit.jsonl").exists()
    finally:
        access.close()
    with pytest.raises(ConfigurationError):
        AuditLog(tmp_path / "legacy.jsonl", retention=Retention())
    assert AuditLog().storage_status()["mode"] == "memory"
    assert AuditLog(tmp_path / "legacy.jsonl").storage_status()["mode"] == "legacy_jsonl"


def test_correlation_threads_and_multiple_writers(tmp_path):
    path = tmp_path / "managed" / "active.jsonl"
    retention = Retention(active_bytes=4096, archive_count=64, total_bytes=262144, lock_timeout_ms=10000)

    def work(index):
        audit = AuditLog(path, retention=retention)
        with request_scope() as correlation:
            audit.emit("policy_granted", app=f"client-{index}")
            audit.emit("request_completed", app=f"client-{index}")
        return correlation

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(work, range(32)))
    audit = AuditLog(path, retention=retention)
    rows = audit.events(include_archives=True)
    assert len(rows) == 64 and len({row["event_id"] for row in rows}) == 64
    for index, correlation in enumerate(ids):
        selected = audit.events(app=f"client-{index}", include_archives=True)
        assert len(selected) == 2 and {row["request_id"] for row in selected} == {correlation}


def test_process_lock_and_crashed_lock_owner(tmp_path):
    sink = storage(tmp_path, lock_timeout_ms=50)
    sink.append(record())
    script = tmp_path / "owner.py"
    signal = tmp_path / "ready"
    script.write_text('import msvcrt,time,sys\nfrom pathlib import Path\n'
        'with open(sys.argv[1],"r+b") as f:\n'
        ' msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)\n'
        ' Path(sys.argv[2]).write_text("ready")\n time.sleep(30)\n')
    process = subprocess.Popen([sys.executable, str(script), str(sink.root / "writer.lock"), str(signal)])
    try:
        deadline = time.monotonic() + 5
        while not signal.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        assert signal.exists()
        with pytest.raises(AuditError):
            sink.append(record(1))
        assert sink.failure == "lock_timeout"
    finally:
        process.kill()
        process.wait(timeout=5)
    sink.append(record(2))
    assert [json.loads(row)["n"] for row in sink.records(10)] == [0,2]


def test_partial_tail_recovery_and_complete_corruption(tmp_path):
    sink = storage(tmp_path)
    sink.append(record())
    active = sink.root / "active.jsonl"
    with active.open("ab") as stream:
        stream.write(b'{"partial":')
    recovered = storage(tmp_path)
    recovered.append(record(1))
    assert recovered.recovery == "partial_tail_removed"
    assert len(recovered.records(10)) == 2
    with active.open("ab") as stream:
        stream.write(b"malformed\n")
    before = active.read_bytes()
    with pytest.raises(AuditError):
        storage(tmp_path).append(record(2))
    assert active.read_bytes() == before


@pytest.mark.parametrize("after", [False, True])
def test_interrupted_rotation_replays_intent(tmp_path, monkeypatch, after):
    sink = storage(tmp_path)
    for index in range(4):
        sink.append(record(index))
    original = Path.rename

    def crash(path, target):
        if path.name == "active.jsonl":
            if after:
                original(path, target)
            raise OSError("synthetic private error")
        return original(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "rename", crash)
        with pytest.raises(AuditError) as error:
            sink.append(record(4))
        assert str(error.value) == "audit_unavailable"
    recovered = storage(tmp_path)
    recovered.append(record(5))
    assert [json.loads(row)["n"] for row in recovered.records(10, archives=True)] == [0,1,2,3,5]
    assert recovered.status()["health"] == "ready"


@pytest.mark.parametrize("after", [False, True])
def test_interrupted_delete_replays_intent(tmp_path, monkeypatch, after):
    sink = storage(tmp_path, archive_count=0)
    for index in range(4):
        sink.append(record(index))
    original = Path.unlink

    def crash(path, *args, **kwargs):
        if path.name.startswith("archive-"):
            if after:
                original(path, *args, **kwargs)
            raise OSError()
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", crash)
        with pytest.raises(AuditError):
            sink.append(record(4))
    sink = storage(tmp_path, archive_count=0)
    sink.append(record(5))
    assert [json.loads(row)["n"] for row in sink.records(10, archives=True)] == [5]


def test_manifest_replacement_recovery_and_initialization(tmp_path):
    sink = storage(tmp_path)
    sink.append(record())
    (sink.root / "state.json").rename(sink.root / "state.new")
    assert len(sink.records(10)) == 1
    assert sink.recovery == "manifest_recovered"
    other = storage(tmp_path / "other")
    other.root.mkdir(parents=True)
    (other.root / "state.new").write_bytes(b'{"interrupted"')
    other.append(record())
    assert len(other.records(10)) == 1


@pytest.mark.parametrize("operation", ["_open", "_flush", "_save", "_owned"])
def test_filesystem_failures_are_visible_and_recoverable(tmp_path, monkeypatch, operation):
    sink = storage(tmp_path)
    for index in range(4):
        sink.append(record(index))

    def fail(*args, **kwargs):
        raise OSError(28, "synthetic secret must not escape")

    with monkeypatch.context() as patch:
        patch.setattr(sink, operation, fail)
        with pytest.raises(AuditError) as error:
            sink.append(record(4))
        assert str(error.value) == "audit_unavailable"
        assert sink.status()["health"] == "degraded"
    sink.append(record(5))
    assert sink.status()["health"] == "ready"


def test_required_audit_precedes_credential_and_provider(tmp_path, store, monkeypatch):
    audit = AuditLog(tmp_path / "managed" / "active.jsonl", retention=Retention())
    engine, access, transport = runtime(store, audit=audit)
    reads = store.reads
    try:
        def fail(*args):
            raise PermissionError("synthetic private path")
        monkeypatch.setattr(audit._storage, "_flush", fail)
        with pytest.raises(AuditError):
            engine.models()
        assert store.reads == reads and transport.calls == []
        assert audit.storage_status()["health"] == "degraded"
    finally:
        engine.close()


def test_unknown_files_and_replaced_identity_preserved(tmp_path):
    sink = storage(tmp_path)
    sink.root.mkdir()
    unknown = sink.root / "active.jsonl"
    unknown.write_bytes(b"legacy user log")
    with pytest.raises(AuditError):
        sink.append(record())
    assert unknown.read_bytes() == b"legacy user log"
    sink = storage(tmp_path / "other")
    sink.append(record())
    active = sink.root / "active.jsonl"
    active.rename(sink.root / "unknown-kept")
    active.write_bytes(record(99))
    with pytest.raises(AuditError):
        sink.append(record())
    assert active.read_bytes() == record(99)


def test_unsafe_paths_and_hardlinks(tmp_path):
    with pytest.raises(OSError):
        safe_path(Path("relative"))
    with pytest.raises(OSError):
        safe_path(tmp_path / "name:stream")
    with pytest.raises(OSError):
        safe_path(tmp_path)
    with pytest.raises(OSError):
        safe_path(tmp_path / "absent")
    sink = storage(tmp_path)
    with pytest.raises(OSError):
        sink._path("../outside")
    sink.append(record())
    active = sink.root / "active.jsonl"
    os.link(active, tmp_path / "hardlink")
    with pytest.raises(AuditError):
        sink.append(record())


def test_reparse_root_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "managed"
    # Directory junction creation requires no Developer Mode or symlink privilege.
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                            capture_output=True, check=False)
    assert result.returncode == 0
    with pytest.raises(AuditError):
        storage(tmp_path).append(record())
    assert list(target.iterdir()) == []


def test_invalid_record_and_manifests_fail_closed(tmp_path):
    sink = storage(tmp_path)
    for data in [b"no-newline", b"x" * 4097 + b"\n", b"broken\n"]:
        with pytest.raises(AuditError):
            sink.append(data)
    assert not sink.root.exists()
    sink.append(record())
    for field, value in [("version", True), ("owner", "../outside"), ("archives", [{}]),
                         ("pending", {}), ("active", -1), ("rotation_ns", -1)]:
        bad = {**state(sink), field: value}
        with pytest.raises(OSError):
            sink._validate_state(bad)
    (sink.root / "state.json").write_bytes(b"bad")
    assert sink.status()["health"] == "degraded"


def test_windows_reader_sharing_violation_recovers(tmp_path):
    sink = storage(tmp_path)
    for index in range(4):
        sink.append(record(index))
    with (sink.root / "active.jsonl").open("rb") as reader:
        with pytest.raises(AuditError):
            sink.append(record(4))
        assert reader.read() == b"".join(record(i) for i in range(4))
    sink.append(record(5))
    assert len(sink.records(10, archives=True)) == 5


def test_windows_readonly_and_manifest_open_failure(tmp_path):
    sink = storage(tmp_path)
    sink.append(record())
    api = WinAPI()
    handle = api.open(str(sink.root / "active.jsonl"), 0x80000000, 1, None, 3, 0, None)
    assert handle != ctypes.c_void_p(-1).value
    try:
        with pytest.raises(AuditError):
            sink.append(record(1))
    finally:
        api.close(handle)
    sink.append(record(2))
    with (sink.root / "state.json").open("rb"):
        for index in range(2):
            sink.append(record(index + 3))
        with pytest.raises(AuditError):
            sink.append(record(5))
    sink.append(record(6))
    assert sink.status()["health"] == "ready"


def test_bound_corruption_and_archive_read_failure(tmp_path):
    sink = storage(tmp_path)
    sink.append(record())
    active = sink.root / "active.jsonl"
    with active.open("ab") as stream:
        stream.write(b"x" * 4096)
    with pytest.raises(AuditError):
        sink.append(record())
    other = storage(tmp_path / "other")
    for index in range(5):
        other.append(record(index))
    archive = other.root / state(other)["archives"][0]["name"]
    archive.write_bytes(b"{\"valid\":1}")
    with pytest.raises(AuditError):
        other.records(10, archives=True)
    archive.write_bytes(b"x" * 4097)
    with pytest.raises(AuditError):
        other.append(record())
    with pytest.raises(OSError):
        other._prune({"archives":[]}, other.retention.total_bytes + 1)


def test_manifest_pending_and_active_ambiguity(tmp_path):
    sink = storage(tmp_path)
    sink.append(record())
    value = state(sink)
    row = {"name": f"archive-{value['owner']}-{'a'*32}.jsonl",
           "file_id":value["active"], "created_ns":time.time_ns()}
    with pytest.raises(OSError):
        sink._validate_state({**value,"pending":{"kind":"delete","row":row}})
    with pytest.raises(OSError):
        sink._recover({**value,"active":None})
    (sink.root / "active.jsonl").rename(sink.root / row["name"])
    (sink.root / "active.jsonl").write_bytes(b"unknown")
    with pytest.raises(OSError):
        sink._recover({**value,"pending":{"kind":"rotate","row":row}})
    assert (sink.root / "active.jsonl").read_bytes() == b"unknown"


def test_open_handle_cleanup_on_wrapping_failure(tmp_path, monkeypatch):
    sink = storage(tmp_path)
    sink.append(record())
    import msvcrt

    def fail(*args, **kwargs):
        raise OSError()

    for module, name in [(msvcrt,"open_osfhandle"),(os,"fdopen"),(os,"fstat")]:
        with monkeypatch.context() as patch:
            patch.setattr(module,name,fail)
            with pytest.raises(OSError):
                sink._open("active.jsonl")
        # Rename would fail if the no-delete-sharing handle had leaked.
        active = sink.root / "active.jsonl"
        moved = active.rename(sink.root / "handle-check")
        moved.rename(active)


def test_actual_process_writers(tmp_path):
    sink = storage(tmp_path, total_bytes=65536, archive_count=16, lock_timeout_ms=10000)
    sink.append(record(-1))
    script = tmp_path / "writer.py"
    script.write_text('import sys,json\nfrom pathlib import Path\n'
        'from cae.audit_storage import JSONLStorage,Retention\n'
        's=JSONLStorage(Path(sys.argv[1]),Retention(active_bytes=4096,total_bytes=65536,'
        'archive_count=16,lock_timeout_ms=10000),lambda b:json.loads(b))\n'
        'for i in range(8): s.append((json.dumps({"worker":sys.argv[2],"n":i})+"\\n").encode())\n')
    workers = [subprocess.Popen([sys.executable,str(script),str(sink.root),str(i)]) for i in range(3)]
    try:
        assert [p.wait(timeout=30) for p in workers] == [0,0,0]
    finally:
        for process in workers:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    rows = [json.loads(row) for row in sink.records(100,archives=True)][1:]
    assert len(rows) == 24 and len({(r["worker"],r["n"]) for r in rows}) == 24


@pytest.mark.parametrize("point", ["append", "rotate", "delete"])
def test_abrupt_process_exit_and_restart(tmp_path, point):
    sink = storage(tmp_path, archive_count=0 if point == "delete" else 7)
    for index in range(4 if point != "append" else 1):
        sink.append(record(index))
    script = tmp_path / "crash.py"
    script.write_text('import os,sys,json\nfrom pathlib import Path\n'
        'from cae.audit_storage import JSONLStorage,Retention\n'
        's=JSONLStorage(Path(sys.argv[1]),Retention(active_bytes=4096,archive_count=int(sys.argv[3])),lambda b:json.loads(b))\n'
        'if sys.argv[2]=="append":\n'
        ' with s._locked():\n'
        '  with s._open("active.jsonl") as f:\n'
        '   f.seek(0,2);f.write(b"partial");s._flush(f);os._exit(77)\n'
        'method="rename" if sys.argv[2]=="rotate" else "unlink"\n'
        'original=getattr(Path,method)\n'
        'def crash(path,*args,**kwargs):\n'
        ' result=original(path,*args,**kwargs)\n'
        ' if path.name=="active.jsonl" or path.name.startswith("archive-"): os._exit(77)\n'
        ' return result\n'
        'setattr(Path,method,crash)\n'
        's.append(b"{\\\"new\\\":true}"+b" "*1011+b"\\n")\n')
    process = subprocess.run([sys.executable,str(script),str(sink.root),point,
                              str(sink.retention.archive_count)],timeout=30,check=False)
    assert process.returncode == 77
    sink.append(record(99))
    rows = [json.loads(row)["n"] for row in sink.records(100,archives=True)]
    assert rows == ([0,99] if point == "append" else [99] if point == "delete" else [0,1,2,3,99])


@pytest.mark.parametrize("fault", ["write", "flush", "close", "unlock"])
def test_append_failure_contract(tmp_path, monkeypatch, fault):
    """A failed write can have committed bytes; it never authorizes later work."""
    import msvcrt

    sink = storage(tmp_path)
    sink.append(record(0))
    original = sink._open

    class Stream:
        def __init__(self, raw):
            self.raw = raw

        def __getattr__(self, name):
            return getattr(self.raw, name)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.raw.close()
            if fault == "close":
                raise OSError(5, "synthetic close failure")

        def write(self, data):
            if fault == "write":
                self.raw.write(data[:7])
                return 7
            return self.raw.write(data)

        def flush(self):
            self.raw.flush()
            if fault == "flush":
                raise OSError(28, "synthetic disk full")

    def opened(name, **kwargs):
        raw = original(name, **kwargs)
        return Stream(raw) if name == "active.jsonl" else raw

    locking = msvcrt.locking

    def unlock_error(fd, mode, length):
        locking(fd, mode, length)
        if mode == msvcrt.LK_UNLCK:
            raise OSError()

    with monkeypatch.context() as patch:
        if fault == "unlock":
            patch.setattr(msvcrt, "locking", unlock_error)
        else:
            patch.setattr(sink, "_open", opened)
        with pytest.raises(AuditError):
            sink.append(record(1))
        assert sink.health == "degraded"
    sink.append(record(2))
    rows = [json.loads(row)["n"] for row in sink.records(10)]
    # A close failure during the pre-write validation can prevent the append;
    # a flush/unlock failure can report failure after a complete record exists.
    assert rows[0] == 0 and rows[-1] == 2
    assert rows in ([0,2], [0,1,2])
    if fault == "write":
        assert rows == [0,2]


def test_registry_preserves_retention_configuration(tmp_path):
    from test_application_registry import image
    from test_broker_lifecycle import configuration

    from cae.registry import ApplicationRegistry

    config, settings, _ = configuration(tmp_path)
    text = settings.runtime.read_text()
    text += '\n[audit]\nmode="managed"\nactive_bytes=4096\narchive_count=2\n'
    settings.runtime.write_text(text)
    registry = ApplicationRegistry(config)
    registry.register("sample", image(tmp_path))
    assert registry.audit.storage_status()["mode"] == "managed_jsonl"
    registry.authorize("sample", "openai", "default", frozenset({"models"}))
    assert audit_retention(settings.runtime.read_text()) == Retention(active_bytes=4096,archive_count=2)


def test_diagnostic_audit_failure_prevents_credential_probe(tmp_path, store, monkeypatch):
    audit = AuditLog(tmp_path / "managed" / "active.jsonl", retention=Retention())
    engine, access, _ = runtime(store, audit=audit)
    seen = []
    monkeypatch.setattr(store, "exists", lambda profile: seen.append(profile))

    def fail(*args):
        raise PermissionError()

    monkeypatch.setattr(audit._storage, "_flush", fail)
    try:
        with pytest.raises(AuditError):
            access.health("app","openai","default")
        assert seen == []
    finally:
        engine.close()


def test_broker_thread_lock_has_bounded_wait(tmp_path):
    import threading

    audit = AuditLog(tmp_path / "managed" / "active.jsonl", retention=Retention(lock_timeout_ms=20))
    ready, release = threading.Event(), threading.Event()

    def hold():
        with audit._lock:
            ready.set()
            release.wait(timeout=5)

    thread = threading.Thread(target=hold)
    thread.start()
    assert ready.wait(timeout=5)
    try:
        with pytest.raises(AuditError):
            audit.emit("broker_status")
        assert audit._storage.failure == "lock_timeout"
    finally:
        release.set()
        thread.join(timeout=5)
    audit.emit("broker_status")
    assert audit.storage_status()["health"] == "ready"


def test_legacy_import_does_not_require_windows_storage_module():
    script = '''import builtins
original = builtins.__import__
def restricted(name, *args, **kwargs):
    if name == "msvcrt": raise ImportError("storage unavailable")
    return original(name, *args, **kwargs)
builtins.__import__ = restricted
from cae.audit import AuditLog
assert AuditLog().emit("broker_status").event == "broker_status"
'''
    result = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, timeout=10)
    assert result.returncode == 0


def test_failure_category_updates_after_a_different_failure(tmp_path, monkeypatch):
    sink = storage(tmp_path)
    sink.append(record())
    sink.failure = "lock_timeout"

    def fail(*args, **kwargs):
        raise PermissionError()

    monkeypatch.setattr(sink, "_open", fail)
    with pytest.raises(AuditError):
        sink.append(record())
    assert sink.failure == "storage_unavailable"
