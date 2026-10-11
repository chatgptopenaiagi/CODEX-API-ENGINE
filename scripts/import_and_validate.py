"""One-time repository-local import. Never deletes the input or prints exceptions."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cae import CAE  # noqa: E402
from cae.credential import CredentialManager  # noqa: E402


def main() -> int:
    report = {
        "Credential import": "FAILED",
        "Secure storage": "FAILED",
        "OpenAI authentication": "FAILED",
        "API connectivity": "FAILED",
        "CAE broker status": "unavailable",
    }
    try:
        manager = CredentialManager()
        # Never silently overwrite an existing profile.
        manager.import_file(ROOT / "apy_key.txt")
        report["Credential import"] = "SUCCESS"
        if manager.exists():
            report["Secure storage"] = "SUCCESS"
        status = CAE().test_connection()
        report["CAE broker status"] = status["broker"] + " (in-process)"
        if status["authentication"] == "valid":
            report["OpenAI authentication"] = "SUCCESS"
        if status["api"] in {"available", "reachable"}:
            report["API connectivity"] = "SUCCESS"
    except Exception:
        pass
    print(json.dumps(report, indent=2))
    return 0 if all(report[k] == "SUCCESS" for k in list(report)[:4]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
