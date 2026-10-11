"""Versioned, bounded JSON protocol and administrator-owned executable enrollment."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import AccessDenied, ConfigurationError
from .pipe_transport import MAX_MESSAGE, Peer, ProtocolError, pipe_path
from .security import identifier


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError()
        result[key] = value
    return result


def decode(data: bytes) -> dict[str, Any]:
    invalid = False
    value: Any = None
    try:
        if not 0 < len(data) <= MAX_MESSAGE:
            raise ValueError()
        value = json.loads(data, object_pairs_hook=_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ProtocolError()))
        if not isinstance(value, dict):
            raise ValueError()
    except Exception:
        invalid = True
    if invalid:
        raise ProtocolError()
    return dict(value)


def encode(value: dict[str, Any]) -> bytes:
    raw = json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(raw) > MAX_MESSAGE:
        raise ProtocolError()
    return raw


@dataclass(frozen=True)
class Enrollment:
    app: str
    image: str
    sha256: str
    admin: bool = False

    def __post_init__(self) -> None:
        identifier(self.app)
        if (not Path(self.image).is_absolute()
                or not re.fullmatch("[a-f0-9]{64}", self.sha256)
                or type(self.admin) is not bool):
            raise ConfigurationError()

    def matches(self, peer: Peer) -> bool:
        return (Path(self.image).resolve() == Path(peer.image).resolve()
                and self.sha256 == peer.sha256)


@dataclass(frozen=True)
class BrokerSettings:
    pipe: str
    runtime: Path
    server: Enrollment
    clients: tuple[Enrollment, ...]

    def authenticate(self, peer: Peer, sid: str) -> Enrollment:
        if peer.sid == sid:
            for client in self.clients:
                if client.matches(peer):
                    return client
        raise AccessDenied()

    @classmethod
    def load(cls, path: Path) -> BrokerSettings:
        result: BrokerSettings | None = None
        try:
            if path.is_symlink() or path.stat().st_size > MAX_MESSAGE:
                raise ValueError()
            value = decode(path.read_bytes())
            if set(value) != {"version", "pipe", "runtime", "server", "clients"}:
                raise ValueError()
            if type(value["version"]) is not int or value["version"] != 1:
                raise ValueError()
            pipe_path(value["pipe"])
            runtime = Path(value["runtime"])
            if not runtime.is_absolute():
                raise ValueError()
            clients = tuple(Enrollment(**row) for row in value["clients"])
            if (not 1 <= len(clients) <= 64
                    or len({Path(row.image).resolve() for row in clients}) != len(clients)):
                raise ValueError()
            result = cls(value["pipe"], runtime, Enrollment(**value["server"]), clients)
        except Exception:
            pass
        if result is None:
            raise ConfigurationError()
        return result


def request(data: bytes) -> dict[str, Any]:
    value = decode(data)
    if (set(value) != {"v", "id", "op", "args"} or type(value["v"]) is not int
            or value["v"] != 1 or not isinstance(value["id"], str)
            or not re.fullmatch("[a-f0-9]{32}", value["id"])
            or not isinstance(value["op"], str) or len(value["op"]) > 32
            or not isinstance(value["args"], dict)):
        raise ProtocolError()
    return value
