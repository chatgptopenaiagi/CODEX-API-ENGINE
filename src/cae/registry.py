"""Explicit operator administration of enrollment; never exposed through client IPC."""

import ctypes
import json
import os
import re
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .audit import AuditLog
from .broker_client import BrokerClient
from .config import audit_retention, parse_config
from .errors import AccessDenied, ConfigurationError
from .ipc_protocol import BrokerSettings, Enrollment, decode
from .pipe_transport import digest, process_peer
from .policy import Rule
from .security import identifier


def _atomic(path: Path, text: str) -> None:
    """Replace one validated configuration file; never leave partial JSON/TOML."""
    if path.is_symlink():
        raise ConfigurationError()
    temporary: str | None = None
    backup: Path | None = None
    cleanup = True
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".cae-edit-", delete=False) as stream:
            temporary = stream.name
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "nt" and path.exists():
            # ReplaceFile preserves the existing destination DACL; plain rename need not.
            replace_file = ctypes.WinDLL("kernel32", use_last_error=True).ReplaceFileW
            replace_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p,
                                    ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]
            replace_file.restype = ctypes.c_int
            backup = Path(temporary + ".previous")
            if not replace_file(str(path), temporary, str(backup), 0, None, None):
                raise OSError()
        else:
            os.replace(temporary, path)
        temporary = None
    except Exception:
        if backup is not None and backup.exists():
            try:
                os.replace(backup, path)
            except OSError:
                # Retain both recovery files if the filesystem cannot restore the original.
                cleanup = False
        raise ConfigurationError() from None
    finally:
        if temporary is not None and cleanup:
            Path(temporary).unlink(missing_ok=True)
        if backup is not None and cleanup:
            backup.unlink(missing_ok=True)


class ApplicationRegistry:
    """Administrative commands require an existing OS-verified admin enrollment.

    Enrollment removal takes effect on the next connection to a development broker.
    Provider policy additions require a controlled restart; credentials are untouched.
    """

    def __init__(self, configuration: Path) -> None:
        self.path = configuration.resolve()
        self.metadata = self.path.with_name(self.path.stem + ".apps.json")
        self.audit = AuditLog(self.path.parent / ".cae" / "administration.jsonl")
        self._audit_configured = False
        if configuration.is_symlink() or self.path.suffix != ".json":
            raise ConfigurationError()

    @contextmanager
    def _locked(self) -> Iterator[tuple[BrokerSettings, str]]:
        import msvcrt

        lock_path = self.path.with_name(self.path.stem + ".apps.lock")
        if lock_path.is_symlink():
            raise ConfigurationError()
        # Authenticate before creating any administrative state.
        settings = BrokerSettings.load(self.path)
        peer = process_peer(os.getpid())
        if not settings.authenticate(peer, peer.sid).admin:
            raise AccessDenied()
        with lock_path.open("a+b") as stream:
            stream.seek(0, 2)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            deadline = time.monotonic() + 5
            while True:
                try:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise ConfigurationError() from None
                    time.sleep(0.025)
            try:
                settings = BrokerSettings.load(self.path)
                if not settings.authenticate(peer, peer.sid).admin:
                    raise AccessDenied()
                if not self._audit_configured:
                    retention = audit_retention(settings.runtime.read_text(encoding="utf-8"))
                    if retention is not None:
                        self.audit = AuditLog(self.path.parent / ".cae" / "administration-managed" / "active.jsonl", retention=retention)
                    self._audit_configured = True
                yield settings, peer.sid
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)

    def _metadata(self) -> dict[str, Any]:
        if not self.metadata.exists():
            return {}
        if self.metadata.is_symlink() or self.metadata.stat().st_size > 65536:
            raise ConfigurationError()
        rows = decode(self.metadata.read_bytes())
        for app, row in rows.items():
            identifier(app)
            if (not isinstance(row, dict) or set(row) != {
                    "registered_at", "principal_sid", "revoked", "revoked_at"}
                    or type(row["revoked"]) is not bool
                    or any(not isinstance(row[key], str) for key in
                           ("registered_at", "principal_sid", "revoked_at"))):
                raise ConfigurationError()
            if not re.fullmatch(r"S-1-\d+(?:-\d+){1,14}", row["principal_sid"]):
                raise ConfigurationError()
            try:
                for key in ("registered_at", "revoked_at"):
                    if row[key]:
                        datetime.fromisoformat(row[key])
            except ValueError:
                raise ConfigurationError() from None
        return rows

    def _write_enrollments(self, settings: BrokerSettings, clients: tuple[Enrollment, ...]) -> None:
        if not 1 <= len(clients) <= 64:
            raise ConfigurationError()
        value = {"version": 1, "pipe": settings.pipe, "runtime": str(settings.runtime),
                 "server": asdict(settings.server), "clients": [asdict(row) for row in clients]}
        text = json.dumps(value, indent=2)
        if len(text.encode()) > 65536:
            raise ConfigurationError()
        _atomic(self.path, text)

    def list(self) -> list[dict[str, Any]]:
        with self._locked() as (settings, _):
            metadata = self._metadata()
            _, rules = parse_config(settings.runtime.read_text(encoding="utf-8"))
            rows = []
            for client in settings.clients:
                rows.append({**asdict(client), **metadata.get(client.app, {}), "revoked": False,
                             "policies": [rule.to_dict() for rule in rules if rule.app == client.app]})
            rows.extend({"app": app, **row, "policies": []} for app, row in metadata.items()
                        if row["revoked"] and not any(item.app == app for item in settings.clients))
            return rows

    def inspect(self, app: str) -> dict[str, Any]:
        identifier(app)
        for row in self.list():
            if row["app"] == app:
                return row
        raise ConfigurationError()

    def register(self, app: str, image: Path) -> dict[str, Any]:
        identifier(app)
        if image.is_symlink() or not image.is_file() or image.suffix.lower() != ".exe":
            raise ConfigurationError()
        image = image.resolve()
        with self._locked() as (settings, sid):
            if any(client.app == app or Path(client.image).resolve() == image for client in settings.clients):
                raise ConfigurationError()
            rows = self._metadata()
            _, policies = parse_config(settings.runtime.read_text(encoding="utf-8"))
            if (len(settings.clients) >= 64 or rows.get(app, {}).get("revoked")
                    or any(rule.app == app for rule in policies)):
                # Do not accidentally reactivate old grants or reuse a revoked identity.
                raise ConfigurationError()
            enrollment = Enrollment(app, str(image), digest(image))
            rows[app] = {"registered_at": datetime.now(UTC).isoformat(), "principal_sid": sid,
                         "revoked": False, "revoked_at": ""}
            encoded = json.dumps(rows, indent=2)
            if len(encoded.encode()) > 65536:
                raise ConfigurationError()
            self.audit.emit("application_change_requested", app=app)
            # Orphan metadata on a failed enrollment is harmless; it cannot grant access.
            _atomic(self.metadata, encoded)
            self._write_enrollments(settings, (*settings.clients, enrollment))
            self.audit.emit("application_registered", app=app)
        return {"app": app, "registered": True, "permissions_granted": False}

    def revoke(self, app: str) -> dict[str, Any]:
        identifier(app)
        with self._locked() as (settings, sid):
            selected = [client for client in settings.clients if client.app == app]
            if not selected or any(client.admin for client in selected):
                raise AccessDenied()
            # Old published brokers cache enrollment. Never imply immediate revocation there.
            effective = "broker_restart"
            try:
                status = BrokerClient(settings.pipe, settings.server.image,
                                      settings.server.sha256, timeout=0.5).get_status()
                if status.get("enrollment_reload") is True:
                    effective = "next_connection"
            except Exception:
                pass
            rows = self._metadata()
            now = datetime.now(UTC).isoformat()
            row = rows.get(app, {"registered_at": "", "principal_sid": sid})
            row.update(revoked=True, revoked_at=now)
            rows[app] = row
            self.audit.emit("application_change_requested", app=app)
            self._write_enrollments(settings, tuple(c for c in settings.clients if c.app != app))
            _atomic(self.metadata, json.dumps(rows, indent=2))
            self.audit.emit("application_revoked", app=app)
        return {"app": app, "revoked": True, "effective": effective}

    def authorize(self, app: str, provider: str, profile: str, operations: frozenset[str],
                  *, models: frozenset[str] = frozenset(), maximum: int = 1000,
                  deny: bool = False, per_minute: int | None = None,
                  concurrent: int | None = None) -> dict[str, Any]:
        identifier(app)
        rule = Rule("app-" + uuid4().hex, app, provider, profile, operations,
                    effect="deny" if deny else "allow", models=models,
                    max_requests_per_day=maximum, max_requests_per_minute=per_minute,
                    max_concurrent_requests=concurrent)
        with self._locked() as (settings, _):
            if not any(client.app == app and not client.admin for client in settings.clients):
                raise AccessDenied()
            providers, rules = parse_config(settings.runtime.read_text(encoding="utf-8"))
            if not any(p.name == provider and p.profile == profile for p in providers):
                raise ConfigurationError()
            previous = next((r for r in rules if (r.app, r.provider, r.profile, r.effect) ==
                             (app, provider, profile, rule.effect)), None)
            if previous is not None:
                rule = replace(rule, id=previous.id,
                    max_requests_per_minute=per_minute if per_minute is not None
                    else previous.max_requests_per_minute,
                    max_concurrent_requests=concurrent if concurrent is not None
                    else previous.max_concurrent_requests)
            # Replace this app's rule for the same provider/profile/effect; preserve other apps.
            kept = tuple(r for r in rules if (r.app, r.provider, r.profile, r.effect) !=
                         (app, provider, profile, rule.effect))
            retention = audit_retention(settings.runtime.read_text(encoding="utf-8"))
            text = "schema_version = 1\n"
            if retention is not None:
                text += '\n[audit]\nmode = "managed"\n'
                text += "".join(key + " = " + str(value) + "\n" for key, value in asdict(retention).items())
            for name, values in (("providers", [asdict(p) for p in providers]),
                                 ("rules", [r.to_dict() for r in (*kept, rule)])):
                for row in values:
                    text += "\n[[" + name + "]]\n"
                    text += "".join(key + " = " + json.dumps(value) + "\n" for key, value in row.items()
                                    if value is not None)
            parse_config(text)
            self.audit.emit("application_change_requested", app=app)
            _atomic(settings.runtime, text)
            self.audit.emit("application_authorized", app=app)
        return {"app": app, "policy_updated": True, "effective": "broker_restart"}
