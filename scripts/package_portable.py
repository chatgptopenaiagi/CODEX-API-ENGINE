"""Create a non-publishable portable candidate; no installer or upload side effects."""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-source", required=True)
    args = parser.parse_args()
    build_source = subprocess.check_output(["git", "rev-parse", args.build_source + "^{commit}"],
                                           cwd=ROOT, text=True).strip()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    dist = ROOT / "dist" / version
    output = dist / "portable-candidate"
    output.mkdir()  # Never replace an earlier candidate.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    source = output / f"CAE-Source-{version}.zip"
    subprocess.run(["git", "archive", "--format=zip", f"--output={source}", commit],
                   cwd=ROOT, check=True)
    portable = output / f"CAE-Portable-{version}-win-x64.zip"
    executables = sorted(dist.glob("*.exe"))
    if len(executables) != 4:
        raise RuntimeError("Expected four validated executables")
    with zipfile.ZipFile(portable, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in executables:
            archive.write(path, path.name)
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.txt", "docs/QUICKSTART_WINDOWS.md",
                     "docs/TROUBLESHOOTING_WINDOWS.md", "docs/DOWNLOAD_AND_INSTALL.md"):
            archive.write(ROOT / name, name)
        archive.write(Path(sys.base_prefix) / "LICENSE.txt", "notices/Python-LICENSE.txt")
        import importlib.metadata
        distribution = importlib.metadata.distribution("pyinstaller")
        copying = next(path for path in distribution.files or [] if str(path).endswith("licenses/COPYING.txt"))
        archive.write(distribution.locate_file(copying), "notices/PyInstaller-COPYING.txt")
        archive.writestr("README-FIRST.txt", (
            f"CAE {version} — LOCAL DEVELOPMENT CANDIDATE, NOT A PUBLIC RELEASE\n"
            "Double-click CAE-Control-Center.exe. No Python installation required.\n"
            "Select only operator-provided configuration. No automatic broker setup.\n"
            "Read docs/QUICKSTART_WINDOWS.md. Existing admin enrollment is required.\n"
            "Unsigned. Windows 10 tested; Windows 11 NOT_RUN. No installer.\n"
            "Redistribution review incomplete: do not publish this candidate.\n"
        ))
    artifacts = []
    for path in [portable, source, *executables, *sorted(dist.glob("*.whl")), *sorted(dist.glob("*.tar.gz"))]:
        artifacts.append({"file": str(path.relative_to(dist)), "size": path.stat().st_size,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {"schema_version": 1, "version": version, "source_archive_commit": commit,
                "build_runtime_commit": build_source, "environment": {"python": platform.python_version(),
                "platform": platform.platform()}, "signature": "UNSIGNED",
                "status": "BLOCKED_NOT_FOR_PUBLICATION", "artifacts": artifacts,
                "limitations": ["License inventory incomplete", "First-run provisioning incomplete",
                                "Windows 11 NOT_RUN", "Installer NOT_IMPLEMENTED"],
                "validation_report": "docs/validation/HUMAN-FIRST-M4.md"}
    (output / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "SHA256SUMS.json").write_text(json.dumps(artifacts, indent=2), encoding="utf-8")
    (output / "SHA256SUMS.txt").write_text("".join(f"{row['sha256']}  {row['file']}\n" for row in artifacts), encoding="utf-8")
    print("Local candidate created. Publication is blocked; see manifest.")


if __name__ == "__main__":
    main()
