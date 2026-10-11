"""Application SDK using only CAE's published BrokerClient interface."""

import json
import os
from pathlib import Path
from typing import Any

from cae import BrokerClient, CAEError

__version__ = "0.4.0"
__all__ = ["CAEClient", "CAEError"]


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


class CAEClient:
    """Discover via explicit descriptor or CAE_CONNECTION_FILE; never replay a call."""

    def __init__(self, connection: str | Path | None = None, *, timeout: float = 35) -> None:
        try:
            selected = connection or os.environ.get("CAE_CONNECTION_FILE")
            if not selected:
                raise ValueError()
            path = Path(selected)
            if path.is_symlink() or path.stat().st_size > 65536:
                raise ValueError()
            config = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique)
            if set(config) != {"pipe", "server_image", "server_sha256"}:
                raise ValueError()
            self._client = BrokerClient(**config, timeout=timeout)
        except Exception:
            raise CAEError() from None

    def request(self, operation: str, **arguments: Any) -> dict[str, Any]:
        return self._client.request(operation, **arguments)

    def connect(self) -> dict[str, Any]:
        """Authenticate and validate protocol v1 using an offline status request."""
        return self.request("status")

    def health(self, provider: str = "openai", profile: str = "default") -> dict[str, Any]:
        return self._client.health(provider, profile)

    def models(self, provider: str = "openai", profile: str = "default") -> dict[str, Any]:
        return self._client.list_models(provider, profile)

    def capabilities(self, profile: str = "default") -> dict[str, Any]:
        return self.request("providers", profile=profile)

    def diagnostics(self, provider: str = "openai", profile: str = "default") -> dict[str, Any]:
        return self._client.diagnostics(provider, profile)
