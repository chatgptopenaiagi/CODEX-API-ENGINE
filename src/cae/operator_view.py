"""Operator-selected broker view; no discovery scans, grants or provider probes."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .broker_client import BrokerClient
from .errors import ConfigurationError
from .ipc_protocol import BrokerSettings, decode
from .pipe_transport import digest
from .registry import ApplicationRegistry


class OperatorView:
    """Selection pins server identity. Every admin operation reauthenticates the image.

    The operator owns the descriptor and config. This is not protection from hostile
    same-account writes. Construction is offline and never starts a broker.
    """

    def __init__(self, path: Path) -> None:
        if path.suffix.lower() != ".json":
            raise ConfigurationError()
        self.path = path.resolve()
        self.settings = BrokerSettings.load(path)
        self.verify()

    def verify(self) -> BrokerSettings:
        current = BrokerSettings.load(self.path)
        if (current.server != self.settings.server or current.pipe != self.settings.pipe
                or current.runtime != self.settings.runtime
                or digest(Path(current.server.image)) != current.server.sha256):
            raise ConfigurationError()
        return current

    def status(self) -> dict[str, Any]:
        current = self.verify()
        return BrokerClient(current.pipe, current.server.image,
                            current.server.sha256, timeout=3).get_status()

    def applications(self) -> list[dict[str, Any]]:
        self.verify()
        return ApplicationRegistry(self.path).list()

    def register(self, app: str, image: Path) -> dict[str, Any]:
        self.verify()
        return ApplicationRegistry(self.path).register(app, image)

    def revoke(self, app: str) -> dict[str, Any]:
        self.verify()
        return ApplicationRegistry(self.path).revoke(app)

    def remember(self, destination: Path) -> None:
        """Create a new explicit portable selection; never overwrite an unknown file."""
        self.verify()
        data = {"schema_version": 1, "configuration": str(self.path),
                "server": asdict(self.settings.server), "pipe": self.settings.pipe,
                "runtime": str(self.settings.runtime)}
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(data, indent=2))

    @classmethod
    def restore(cls, source: Path) -> "OperatorView":
        if source.is_symlink() or source.stat().st_size > 65536:
            raise ConfigurationError()
        value = decode(source.read_bytes())
        if (set(value) != {"schema_version", "configuration", "server", "pipe", "runtime"}
                or type(value["schema_version"]) is not int or value["schema_version"] != 1
                or not isinstance(value["configuration"], str)
                or not Path(value["configuration"]).is_absolute()):
            raise ConfigurationError()
        result = cls(Path(value["configuration"]))
        if (value["server"] != asdict(result.settings.server)
                or value["pipe"] != result.settings.pipe
                or value["runtime"] != str(result.settings.runtime)):
            raise ConfigurationError()
        return result
