"""Generate checksums for future CI/build artifacts; never changes software artifacts."""

import hashlib
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    dist = ROOT / "dist" / version
    rows = [
        {"File": path.name, "Hash": hashlib.sha256(path.read_bytes()).hexdigest().upper()}
        for path in sorted(dist.iterdir())
        if path.is_file() and path.suffix in {".exe", ".whl", ".gz"}
    ]
    if len(rows) < 3:
        raise SystemExit("Checksum generation: FAILED")
    (dist / "SHA256SUMS.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print("Checksum generation: SUCCESS")


if __name__ == "__main__":
    main()
