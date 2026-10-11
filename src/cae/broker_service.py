"""Independent Windows process: OS-authenticated local IPC around AccessRuntime."""

import argparse
import os
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .access import AccessRuntime
from .audit import correlated
from .config import load_runtime
from .errors import AccessDenied, AuditError, CAEError
from .ipc_protocol import BrokerSettings, Enrollment, encode, request
from .pipe_transport import Pipe, ProtocolError, process_peer
from .security import identifier
from .version import __version__


class BrokerServer:
    def __init__(self, settings: BrokerSettings, runtime: AccessRuntime,
                 *, configuration: Path | None = None) -> None:
        self.settings, self.runtime = settings, runtime
        self.configuration = configuration
        self.identity = process_peer(os.getpid())
        if not settings.server.matches(self.identity):
            raise AccessDenied()
        self.stopping = threading.Event()
        self.ready = threading.Event()
        self.workers: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._active = 0
        self._rejected = 0

    def dispatch(self, client: Enrollment, operation: str,
                 args: dict[str, Any]) -> dict[str, Any]:
        app = client.app
        if operation in {"status", "stop"}:
            if args:
                raise ProtocolError()
            if operation == "stop":
                if not client.admin:
                    raise AccessDenied()
                self.runtime.audit_log.emit("broker_stopping", app=app)
                self.stopping.set()
            self.runtime.audit_log.emit("broker_status", app=app)
            return {"broker": "stopping" if self.stopping.is_set() else "ready",
                    "broker_mode": "named_pipe", "broker_pid": os.getpid(),
                    "version": __version__, "app": app, "max_connections": 8,
                    "enrollment_reload": self.configuration is not None,
                    "active_connections": self._active, "rejected_connections": self._rejected}
        if operation not in {"health", "diagnostics", "models", "chat", "embeddings",
                             "providers", "usage", "audit", "policies"}:
            raise AccessDenied()
        allowed = {"provider", "profile"}
        if operation == "health":
            allowed.add("probe")
        if operation in {"chat", "embeddings"}:
            allowed |= {"model", "text", "max_tokens"}
        if set(args) - allowed:
            raise ProtocolError()
        name, profile = args.get("provider", "openai"), args.get("profile", "default")
        if not isinstance(name, str) or not isinstance(profile, str):
            raise ProtocolError()
        identifier(name)
        identifier(profile)
        if operation in {"health", "diagnostics"}:
            probe = args.get("probe", False)
            if type(probe) is not bool:
                raise ProtocolError()
            result = self.runtime.health(app, name, profile, probe=probe)
            return {**result, "broker_mode": "named_pipe", "broker_pid": os.getpid()}
        if operation == "providers":
            return {"providers": self.runtime.providers(app, profile)}
        if operation == "usage":
            return self.runtime.usage(app, name, profile)
        if operation == "audit":
            return {"events": self.runtime.audit(app)[-50:]}
        if operation == "policies":
            return {"rules": self.runtime.policies(app)}
        model, text = args.get("model"), args.get("text")
        if ((model is not None and not isinstance(model, str))
                or (text is not None and not isinstance(text, str))):
            raise ProtocolError()
        return self.runtime.execute(app, name, profile, operation, model=model,
                                    text=text, max_tokens=args.get("max_tokens", 256))

    @correlated
    def _session(self, pipe: Pipe) -> None:
        correlation = "0" * 32
        app = "unknown"
        result: dict[str, Any] = {}
        error: str | None = None
        try:
            value = request(pipe.receive(2))
            correlation = value["id"]
            settings = self.settings
            if self.configuration is not None:
                settings = BrokerSettings.load(self.configuration)
                # Enrollment is reloadable; listener/runtime/server identity are pinned until restart.
                if (settings.pipe != self.settings.pipe or settings.runtime != self.settings.runtime
                        or settings.server != self.settings.server):
                    raise AccessDenied()
            client = settings.authenticate(pipe.peer(), self.identity.sid)
            app = client.app
            self.runtime.audit_log.emit("ipc_authenticated", app=app)
            result = self.dispatch(client, value["op"], value["args"])
        except CAEError as exc:
            error = exc.code
        except Exception:
            error = "broker_unavailable"
        if error:
            with self._lock:
                self._rejected += 1
        try:
            self.runtime.audit_log.emit("ipc_denied" if error else "ipc_result",
                                        app=app, error_code=error or "none")
        except AuditError:
            # Return a fixed failure even if the sink cannot record that failure.
            # A completed provider call is not replayed when its audit write failed.
            error, result = "audit_unavailable", {}
        envelope = {"v": 1, "id": correlation, "ok": error is None, "result": result,
                    "error": error, "broker_pid": os.getpid()}
        try:
            raw = encode(envelope)
        except (ValueError, ProtocolError):
            envelope.update(ok=False, result={}, error="invalid_protocol")
            raw = encode(envelope)
        pipe.send(raw)
        if pipe.receive(2) != b"OK":
            raise ProtocolError()

    def _worker(self, pipe: Pipe) -> None:
        try:
            while not self.stopping.is_set():
                try:
                    pipe.accept(self.stopping)
                    with self._lock:
                        self._active += 1
                    try:
                        self._session(pipe)
                    finally:
                        with self._lock:
                            self._active -= 1
                except Exception:
                    # Deliberate boundary: never expose request/backend exception text.
                    pass
                finally:
                    pipe.disconnect()
        finally:
            pipe.close()

    def serve(self) -> None:
        pipes: list[Pipe] = []
        try:
            for index in range(8):
                pipes.append(Pipe.listener(self.settings.pipe, self.identity.sid, first=index == 0))
            self.runtime.audit_log.emit("broker_started")
            for pipe in pipes:
                thread = threading.Thread(target=self._worker, args=(pipe,), daemon=False)
                self.workers.append(thread)
                thread.start()
            self.ready.set()
            self.stopping.wait()
        finally:
            self.stopping.set()
            if not self.workers:
                for pipe in pipes:
                    pipe.close()
            for thread in self.workers:
                thread.join()
            self.runtime.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="CAE-Broker")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            peer = process_peer(os.getpid())
            pipe = Pipe.listener("cae-smoke-" + str(os.getpid()), peer.sid, first=True)
            pipe.close()
            return 0
        if args.config is None:
            raise ProtocolError()
        settings = BrokerSettings.load(args.config)
        BrokerServer(settings, load_runtime(settings.runtime), configuration=args.config).serve()
        return 0
    except (Exception, KeyboardInterrupt):
        # Windowed builds have no terminal; CLI supervisor reports fixed status.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
