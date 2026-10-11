"""Audit only Git-eligible files, without traversing ignored local credential inputs."""

import argparse
import concurrent.futures
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_PARTS = {"apy_key.txt", ".venv", ".tmp", ".cache", "__pycache__", "dist"}
BLOCKED_SUFFIXES = {".pem", ".p12", ".pfx", ".key", ".keystore", ".pyc", ".exe", ".whl"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gitleaks", type=Path, required=True)
    args = parser.parse_args()
    scanner = args.gitleaks.resolve()
    output = ROOT / ".tmp/publication/audit"
    output.mkdir(parents=True, exist_ok=True)
    config = output / "scanner.toml"
    config.write_text("[extend]\nuseDefault = true\n", encoding="utf-8")
    candidates = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    names = sorted(set(name for name in candidates if name))
    blocked = []
    for name in names:
        path = ROOT / name
        if (
            path.is_symlink()
            or path.suffix.lower() in BLOCKED_SUFFIXES
            or any(
                p.lower() in BLOCKED_PARTS or p.lower().startswith(".env") for p in Path(name).parts
            )
            or (name.startswith("build/") and name != "build/README.md")
        ):
            blocked.append(name)
    if blocked:
        print(json.dumps({"audit": "FAILED", "blocked_paths": blocked}))
        return 1

    def scan(item: tuple[int, str]) -> dict:
        index, name = item
        report = output / f"{index}.json"
        result = subprocess.run(
            [
                str(scanner),
                "dir",
                str(ROOT / name),
                "--config",
                str(config),
                "--redact=100",
                "--no-banner",
                "--no-color",
                "--log-level",
                "error",
                "--max-archive-depth",
                "4",
                "--ignore-gitleaks-allow",
                "--report-format",
                "json",
                "--report-path",
                str(report),
            ],
            cwd=ROOT,
            capture_output=True,
        )
        findings = json.loads(report.read_text()) if report.exists() else []
        return {
            "path": name,
            "exit": result.returncode,
            "rules": sorted({finding["RuleID"] for finding in findings}),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(scan, enumerate(names)))
    failures = [row for row in results if row["exit"] != 0 or row["rules"]]
    summary = {
        "audit": "FAILED" if failures else "SUCCESS",
        "file_count": len(names),
        "scanner": "gitleaks",
        "findings": failures,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(names, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
