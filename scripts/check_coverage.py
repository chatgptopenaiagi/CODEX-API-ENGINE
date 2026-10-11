"""Enforce measured coverage floors for the runtime trust boundary, not UI code."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRITICAL = {
    "access", "api", "audit", "broker", "broker_client", "broker_control", "broker_service",
    "config", "credential", "engine", "ipc_protocol", "pipe_transport", "policy", "providers",
    "registry", "security",
}


def main() -> None:
    report = json.loads((ROOT / ".tmp/coverage.json").read_text())
    actual = {Path(name).stem: row["summary"]["percent_covered"]
              for name, row in report["files"].items()
              if name.replace("\\", "/").startswith("src/cae/")}
    failed = sorted(name for name in CRITICAL if actual.get(name, 0) < 95)
    if report["totals"]["percent_covered"] < 90 or failed:
        raise SystemExit("Coverage gate failed: " + ", ".join(failed or ["overall"]))
    print("Coverage gates passed: overall >=90%; 16 security/runtime modules >=95%.")


if __name__ == "__main__":
    main()
