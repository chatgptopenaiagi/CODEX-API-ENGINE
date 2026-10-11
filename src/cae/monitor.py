"""Opt-in bounded-frequency monitoring; no network calls merely from import/init."""

import threading
from typing import Any

from .engine import CAE
from .errors import ConfigurationError


class HealthMonitor:
    def __init__(self, engine: CAE, interval: float = 300) -> None:
        if not 30 <= interval <= 86400:
            raise ConfigurationError()
        self._engine = engine
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def poll(self) -> dict[str, Any]:
        return self._engine.test_connection()

    def snapshot(self) -> dict[str, Any]:
        return self._engine.get_status()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True, name="cae-health")
            self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            self.poll()
            self._stop.wait(self._interval)

    def stop(self, timeout: float = 20) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    def __enter__(self) -> HealthMonitor:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
