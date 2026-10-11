"""Metadata-only evidence and continuity contracts. No ARX/CGC implementation assumed."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from .engine import CAE
from .security import identifier


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    record_id: str
    observed_at: str
    system: str
    sdk_version: str
    broker: str
    policy: str
    provider_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceSink(Protocol):
    def record(self, evidence: EvidenceRecord) -> None: ...


class ContinuitySink(Protocol):
    def checkpoint(self, evidence: EvidenceRecord) -> None: ...


def snapshot(engine: CAE, system: str) -> EvidenceRecord:
    """Offline observation, not a trust decision or proof of external identity."""
    identifier(system)
    diagnostics = engine.diagnostics()
    health = diagnostics["health"]
    return EvidenceRecord(
        uuid4().hex,
        datetime.now(UTC).isoformat(),
        system,
        diagnostics["sdk_version"],
        health["broker"],
        health["policy"],
        health["api"],
    )
